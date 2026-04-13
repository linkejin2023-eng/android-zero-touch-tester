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

    args = parser.parse_args()

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

def run_job(args, config, db):
    raw_build = args.build
    build_type = args.type
    source_type = args.source
    
    # 標準化版本號
    build_num = get_full_build_name(raw_build)
    
    # SKU 判定 (優先使用參數，否則自動判定)
    sku = args.sku if args.sku else parse_sku_from_build(build_num, source_type)
    
    # 3. 尋找 Image 元數據 (包含完整名稱與 JSON 路徑)
    # 支援注入模式：傳入 args.remote_path
    build_meta = find_source_zip(config, raw_build, build_type, source_type, sku=sku, remote_path=getattr(args, 'remote_path', None))
    
    if not build_meta:
        error_msg = f"Could not find source zip for {raw_build} in remote {source_type} folders."
        logging.error(error_msg)
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
                db.update_status(full_build_name, build_type, "ERROR: Image Transfer Failed")
                return

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

            # 7. 執行測試
            main_py = os.path.abspath("main.py")
            # 使用 sys.executable 以確保與當前 venv 環境一致
            cmd = get_flash_command(main_py, local_zip, sku)
            cmd[0] = sys.executable 
            
            # 加入 Workspace 配置與報表路徑
            cmd.extend(["--config-dir", ws_dir])
            cmd.extend(["--report-dir", os.path.join(ws_dir, "report")])
            
            log_out.write(f"Executing: {' '.join(cmd)}\n")
            log_out.write("-" * 40 + "\n")
            log_out.flush()
            
            # 執行並實時導向輸出
            process = subprocess.Popen(cmd, stdout=log_out, stderr=subprocess.STDOUT, text=True)
            process.wait()
            
            status = "SUCCESS" if process.returncode == 0 else "FAILED"
            log_out.write(f"\n" + "-" * 40 + "\n")
            log_out.write(f"Job Finished with status: {status} (Code: {process.returncode})\n")
            
            db.update_status(full_build_name, build_type, status)
            logging.info(f"Job Finished: {status}")

    except Exception as e:
        logging.error(f"Fatal error during job execution: {e}")
        db.update_status(full_build_name, build_type, f"EXCEPTION: {str(e)}")
        with open(log_file, "a") as log_out:
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
                # 刪除 zip 檔案
                for f in os.listdir(ws_path):
                    if f.endswith(".zip"):
                        file_to_del = os.path.join(ws_path, f)
                        logging.info(f"Cleanup: Removing old image {file_to_del}")
                        os.remove(file_to_del)
    except Exception as e:
        logging.error(f"Cleanup failed: {e}")

if __name__ == "__main__":
    main()
