import os
import sys
import argparse
import shutil
import subprocess
import logging
import time
from datetime import datetime

# 將專案根目錄加入路徑
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from monitor.database import BuildDatabase
from monitor.logic import (
    parse_sku_from_build, 
    get_workspace_dir, 
    get_flash_command, 
    find_source_zip,
    get_full_build_name
)
from framework.lock_manager import LockManager
import yaml

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s [%(levelname)s] %(message)s',
                   handlers=[logging.StreamHandler()])

def main():
    parser = argparse.ArgumentParser(description="SSH-Triggered Sanity Test Job")
    parser.add_argument("--build", type=str, required=True, help="Build number (e.g. 02.01.06 or timestamp for daily)")
    parser.add_argument("--type", type=str, default="user", choices=["user", "userdebug"], help="Build type")
    parser.add_argument("--source", type=str, required=True, choices=["release", "daily"], help="Build source folder")
    parser.add_argument("--sku", type=str, choices=["gms", "china"], help="Manually override SKU")
    parser.add_argument("--config", type=str, default="configs/monitor_config.yaml", help="Path to config file")
    parser.add_argument("--check-only", action="store_true", help="Only verify connectivity and paths, skip execution")
    parser.add_argument("--remote-path", type=str, help="Inject absolute path to remote fastboot.zip (skips searching)")

    args, unknown = parser.parse_known_args()
    
    # 統一 SKU 名稱 (相容舊有 nogms 傳入)
    if "--sku" in sys.argv:
        idx = sys.argv.index("--sku")
        if idx + 1 < len(sys.argv) and sys.argv[idx+1] == "nogms":
            args.sku = "china"

    # 1. 載入設定
    if not os.path.exists(args.config):
        print(f"Error: Config file not found at {args.config}")
        sys.exit(1)
        
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)

    db = BuildDatabase(config.get('history_db_path', 'monitor/history.db'))
    lock = LockManager(config.get('lock_file', 'test.lock'))

    # 2. 阻塞式獲取鎖
    logging.info(f"Task queued for Build: {args.build}, Source: {args.source}")
    lock.acquire(blocking=True)

    try:
        run_job(args, config, db)
    finally:
        lock.release()

def generate_emergency_json(full_build_name, variant, status, category, test_name, message):
    """產出緊急摘要 JSON，確保 CI 通知信能發出報警"""
    try:
        emergency_summary = {
            "status": status,
            "version": full_build_name,
            "variant": variant,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "stats": {"total": 0, "passed": 0, "failed": 0, "error": 1, "exempt": 0, "pass_rate": "0.0%"},
            "failed_cases": [{"category": category, "test_name": test_name, "message": message}]
        }
        with open("test_summary.json", "w") as f:
            import json
            json.dump(emergency_summary, f, indent=4)
        logging.info(f"Emergency JSON generated: {status} - {message}")
    except Exception as e:
        logging.error(f"Failed to generate emergency JSON: {e}")

def run_job(args, config, db):
    raw_build = args.build
    build_type = args.type
    source_type = args.source
    
    # [CRITICAL SAFETY] 刪除舊的測試摘要，防止搬運失敗時誤讀舊資料
    if os.path.exists("test_summary.json"):
        os.remove("test_summary.json")
    
    # 標準化版本號 (只有 Release 需要補 REL_ 前綴)
    if source_type == "release":
        build_num = get_full_build_name(raw_build)
    else:
        build_num = raw_build
    
    # SKU 判定 (優先使用參數，否則自動判定)
    sku = args.sku if args.sku else parse_sku_from_build(build_num, source_type)
    
    # 3. 尋找 Image 元數據 (包含完整名稱與 JSON 路徑)
    # 支援注入模式：傳入 args.remote_path
    build_meta = find_source_zip(config, raw_build, build_type, source_type, sku=sku, remote_path=getattr(args, 'remote_path', None))
    
    if not build_meta:
        error_msg = f"Could not find source zip for {raw_build} in remote {source_type} folders."
        logging.error(error_msg)
        generate_emergency_json(build_num, build_type, "INFRA_ERROR", "Source", "Image Search", error_msg)
        db.add_build(build_num, build_type, "N/A", "ERROR: Source Missing")
        return

    full_build_name = build_meta['full_build_name']
    
    # 4. 建立 Workspace (使用完整名稱)
    base_ws = config.get('workspace_base_dir', './workspaces')
    ws_dir = get_workspace_dir(base_ws, full_build_name, build_type)
    os.makedirs(ws_dir, exist_ok=True)
    os.makedirs(os.path.join(ws_dir, "report"), exist_ok=True)
    os.makedirs(os.path.join(ws_dir, "artifacts"), exist_ok=True)
    
    # 紀錄到 DB (狀態: RUNNING)
    db.add_build(full_build_name, build_type, ws_dir, "RUNNING")
    
    log_file = os.path.join(ws_dir, "console.log")
    logging.info(f"Execution started. Workspace: {ws_dir}")
    
    try:
        with open(log_file, "a") as log_out:
            log_out.write(f"--- Job Started at {datetime.now().isoformat()} ---\n")
            log_out.write(f"Build: {full_build_name}, Type: {build_type}, Source: {source_type}, SKU: {sku}\n\n")
            
            # --- Check-only Mode Exit Point ---
            if getattr(args, 'check_only', False):
                msg = "[CHECK-ONLY] Remote source found and workspace ready. Exiting as requested."
                logging.info(msg)
                log_out.write(f"{msg}\n")
                db.update_status(full_build_name, build_type, "CHECKED")
                return

            # 5. 搬運 Image
            source_zip = build_meta['zip_path']
            local_zip = os.path.join(ws_dir, config.get('fastboot_filename', 'fastboot.zip'))
            
            log_out.write(f"Transferring image from {source_zip}...\n")
            log_out.flush()
            
            # 判斷是否為本地路徑 (不含冒號)
            if ":" not in source_zip:
                log_out.write("Detecting LOCAL source path. Skipping SSH.\n")
                rsync_zip_cmd = ["rsync", "-av", "--progress", source_zip, local_zip]
            else:
                rsync_zip_cmd = ["rsync", "-av", "--partial", "-e", "ssh", source_zip, local_zip]
            
            # 實作重試機制 (最多 3 次)
            max_retries = 3
            success = False
            for attempt in range(1, max_retries + 1):
                log_out.write(f"Transfer attempt {attempt}/{max_retries}...\n")
                log_out.flush()
                result = subprocess.run(rsync_zip_cmd, stdout=log_out, stderr=subprocess.STDOUT)
                
                if result.returncode == 0:
                    success = True
                    log_out.write("Image transfer success.\n\n")
                    break
                else:
                    log_out.write(f"Transfer failed with code {result.returncode}. ")
                    if attempt < max_retries:
                        wait_time = attempt * 5
                        log_out.write(f"Retrying in {wait_time}s...\n")
                        log_out.flush()
                        time.sleep(wait_time)
                    else:
                        log_out.write("All retry attempts failed.\n")

            if not success:
                error_msg = f"CRITICAL: Image transfer failed after {max_retries} attempts."
                logging.error(error_msg)
                generate_emergency_json(full_build_name, build_type, "INFRA_ERROR", "Infrastructure", "Image Transfer", error_msg)
                db.update_status(full_build_name, build_type, "ERROR: Image Transfer Failed")
                return 1

            # 6. 同步 build_info.json (如果有)
            source_json = build_meta['json_path']
            local_json = os.path.join(ws_dir, "build_info.json")
            log_out.write(f"Checking for remote config: {source_json}...\n")
            
            rsync_json_cmd = ["rsync", "-av", "-e", "ssh", source_json, local_json]
            json_result = subprocess.run(rsync_json_cmd, stdout=log_out, stderr=subprocess.STDOUT)
            if json_result.returncode == 0:
                log_out.write("專屬 build_info.json 同步成功。\n\n")
            else:
                log_out.write("未發現專屬 build_info.json，將在執行時使用預設配置。\n\n")
            log_out.flush()

            # 6.5 [Pre-flight] Device Connectivity Check
            log_out.write("Checking device connectivity before flashing...\n")
            adb_found = False
            fb_found = False
            adb_count = 0
            fb_count = 0

            # 檢查 ADB (系統全域)
            try:
                adb_res = subprocess.run(["adb", "devices"], capture_output=True, text=True)
                adb_count = len(adb_res.stdout.strip().split('\n')[1:])
                adb_found = True
            except FileNotFoundError:
                log_out.write("Warning: 'adb' command not found in system PATH. Skipping ADB check.\n")

            # 檢查 Fastboot (系統全域)
            try:
                fb_res = subprocess.run(["fastboot", "devices"], capture_output=True, text=True)
                fb_lines = [l for l in fb_res.stdout.strip().split('\n') if l.strip()]
                fb_count = len(fb_lines)
                fb_found = True
            except FileNotFoundError:
                log_out.write("Note: 'fastboot' command not found in system PATH (expected for per-build bundled tools). Skipping Pre-flash Fastboot check.\n")

            # 判定邏輯
            if adb_found or fb_found:
                if adb_count == 0 and fb_count == 0:
                    error_msg = "CRITICAL: No device detected in ADB (or Fastboot if available). Aborting job."
                    logging.error(error_msg)
                    log_out.write(f"{error_msg}\n")
                    generate_emergency_json(full_build_name, build_type, "INFRA_ERROR", "Infrastructure", "Device Connectivity", error_msg)
                    db.update_status(full_build_name, build_type, "ERROR: No Device")
                    return 1
            else:
                # 兩者都找不到指令 (環境問題)
                error_msg = "CRITICAL: Both 'adb' and 'fastboot' commands are missing from system PATH."
                logging.error(error_msg)
                log_out.write(f"{error_msg}\n")
                generate_emergency_json(full_build_name, build_type, "INFRA_ERROR", "Infrastructure", "Tool Missing", error_msg)
                return 1

            # 7. 執行測試
            main_py = os.path.abspath("main.py")
            # 使用 sys.executable 以確保與當前 venv 環境一致
            cmd = get_flash_command(main_py, local_zip, sku)
            cmd[0] = sys.executable 
            
            # 加入 Workspace 配置、報表路徑與元數據 (用於報表命名)
            cmd.extend(["--config-dir", ws_dir])
            cmd.extend(["--report-dir", os.path.join(ws_dir, "report")])
            cmd.extend(["--build", full_build_name])
            cmd.extend(["--type", build_type])
            
            log_out.write(f"Executing: {' '.join(cmd)}\n")
            log_out.write("-" * 40 + "\n")
            log_out.flush()
            
            # 執行並實時導向輸出
            process = subprocess.Popen(cmd, stdout=log_out, stderr=subprocess.STDOUT, text=True)
            process.wait()
            
            # Map exit codes to status strings
            if process.returncode == 0:
                status = "SUCCESS"
            elif process.returncode == 2:
                status = "PARTIAL"
            else:
                status = "FAILED"
                
            log_out.write(f"\n" + "-" * 40 + "\n")
            log_out.write(f"Job Finished with status: {status} (Code: {process.returncode})\n")

            # 8. [V2.3 新增] 產物回傳 (Handback Artifacts to Image Server)
            if source_zip:
                try:
                    log_out.write(f"\n[Handback] Transferring reports back to Image Server...\n")
                    remote_parts = source_zip.split(":")
                    if len(remote_parts) == 2:
                        remote_host = remote_parts[0]
                        remote_dir = os.path.dirname(remote_parts[1])
                        target_report_dir = os.path.join(remote_dir, "test_reports")
                        
                        # 在遠端建立目錄
                        mkdir_cmd = ["ssh", remote_host, f"mkdir -p {target_report_dir}"]
                        subprocess.run(mkdir_cmd, stdout=log_out, stderr=subprocess.STDOUT)
                        
                        # 同步報表
                        local_report_dir = os.path.join(ws_dir, "report/") # 注意結尾斜線
                        rsync_back_cmd = ["rsync", "-av", "-e", "ssh", local_report_dir, f"{remote_host}:{target_report_dir}/"]
                        subprocess.run(rsync_back_cmd, stdout=log_out, stderr=subprocess.STDOUT)
                        log_out.write(f"[Handback] Reports synced to: {target_report_dir}\n")
                except Exception as he:
                    log_out.write(f"[Handback Fail] Could not sync reports back: {he}\n")
            
            db.update_status(full_build_name, build_type, status)
            logging.info(f"Job Finished: {status}")
            return process.returncode

    except Exception as e:
        logging.error(f"Fatal error during job execution: {e}")
        # 捕捉任何未預期的程式崩潰並發報
        generate_emergency_json(full_build_name if 'full_build_name' in locals() else "UNKNOWN", 
                                build_type if 'build_type' in locals() else "UNKNOWN", 
                                "ERROR", "Script", "Fatal Exception", str(e))
        db.update_status(full_build_name if 'full_build_name' in locals() else "UNKNOWN", 
                         build_type if 'build_type' in locals() else "UNKNOWN", 
                         f"EXCEPTION: {str(e)}")
        with open(log_file if 'log_file' in locals() else "emergency_console.log", "a") as log_out:
            log_out.write(f"\n[CRITICAL EXCEPTION] {e}\n")

    # 6. 智慧清理
    perform_cleanup(config, db)

def perform_cleanup(config, db):
    """保留最新 2 份 Zip"""
    try:
        limit = config.get('max_retention_zips', 2)
        recent = db.get_recent_zips(limit=limit)
        protected_paths = [os.path.abspath(r[2]) for r in recent]
        
        ws_base = config.get('workspace_base_dir', './workspaces')
        for entry in os.listdir(ws_base):
            ws_path = os.path.abspath(os.path.join(ws_base, entry))
            if os.path.isdir(ws_path) and ws_path not in protected_paths:
                # 遍歷 workspace 內部進行精細清理
                for item in os.listdir(ws_path):
                    item_path = os.path.join(ws_path, item)
                    # 1. 刪除所有 zip 檔案
                    if item.endswith(".zip"):
                        logging.info(f"Cleanup: Removing image {item_path}")
                        os.remove(item_path)
                    # 2. 刪除所有資料夾，但保留 report 和 artifacts
                    elif os.path.isdir(item_path):
                        if item not in ["report", "artifacts"]:
                            logging.info(f"Cleanup: Removing large directory {item_path}")
                            shutil.rmtree(item_path)
    except Exception as e:
        logging.error(f"Cleanup failed: {e}")

if __name__ == "__main__":
    import sys
    sys.exit(main())
