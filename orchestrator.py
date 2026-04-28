#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
orchestrator.py - 統一主控器 (Unified Orchestrator) v2
架構：Build -> Test -> Unified Notification
特性：純 Python 標準庫實現，無第三方套件依賴 (No YAML/Paramiko)
"""

import os
import sys
import json
import subprocess
import shutil
from datetime import datetime

# === 配置區 (Constants) ===
TEST_SERVER = "10.192.220.17"  # 測試機 IP
TEST_USER = "franck_lin"
TEST_DIR = "/home/franck_lin/auto_test"
IMAGE_SERVER_IP = "10.192.188.16"
RECIPIENTS = "Nick_Chuang@pegatroncorp.com,Billy_Chen@pegatroncorp.com,Franck_Lin@pegatroncorp.com"

# 獲取腳本所在目錄
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 智慧路徑定位 (支援扁平結構或目錄結構)
potential_paths = [
    os.path.join(BASE_DIR, "T70_build_v2.bash"),
    os.path.join(BASE_DIR, "ci-integration", "build_server", "T70_build_v2.bash")
]
BUILD_WRAPPER = potential_paths[0]
for p in potential_paths:
    if os.path.exists(p):
        BUILD_WRAPPER = p
        break

def run_local(cmd, capture=True):
    """執行本地指令並捕捉輸出 (Python 3.6+ 相容版)"""
    print(f"[EXEC] {cmd}")
    try:
        if capture:
            # Python 3.6 不支援 capture_output=True, 改用 PIPE
            result = subprocess.run(
                cmd, shell=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                universal_newlines=True, 
                check=False
            )
            return result.returncode, result.stdout, result.stderr
        else:
            result = subprocess.run(cmd, shell=True, check=False)
            return result.returncode, "", ""
    except Exception as e:
        return -1, "", str(e)

def send_unified_mail(subject, content):
    """透過系統 mutt 指令發信 (使用 Python 內建 PIPE，保證反斜線與特殊字元不被轉義)"""
    print(f"[MAIL] Sending: {subject}")
    try:
        # 清理並分解收件人清單
        recipient_list = [r.strip() for r in RECIPIENTS.split(',')]
        # 建立 mutt 指令陣列
        cmd = ["mutt", "-s", subject, "--"] + recipient_list
        
        # [FIXED] Python 3.6 不支援 text=True, 必須使用 universal_newlines=True
        subprocess.run(cmd, input=content, universal_newlines=True, check=True)
    except Exception as e:
        # 如果 mutt 執行失敗，則回退到最基礎的日誌記錄
        print(f"[ERROR] Failed to send mail via mutt: {e}")
        print("--- FALLBACK MAIL CONTENT ---")
        print(f"Subject: {subject}")
        print(content)
        print("------------------------------")

def process_variant(branch, variant, timestamp, dry_run=False, only_test=False):
    """處理單一 Variant 的完整生命週期：編譯 -> 測試 -> 發信"""
    mode_str = ""
    if dry_run: mode_str += "[DRY-RUN] "
    if only_test: mode_str += "[ONLY-TEST] "
    
    print(f"\n{'='*60}\n>>> Processing {branch} ({variant}) ID: {timestamp} {mode_str}\n{'='*60}")

    # 1. 執行編譯
    if not only_test:
        build_cmd = f"bash {BUILD_WRAPPER} {branch} {variant} {timestamp}"
        if dry_run:
            print(f"[DRY-RUN] Would execute: {build_cmd}")
        else:
            rc, stdout, stderr = run_local(build_cmd)
            if rc != 0:
                msg = f"Stage: Build Process\nResult: Failed (RC: {rc})\n\n[ERROR DETAILS]\n{stderr}\n\n[STDOUT]\n{stdout}"
                send_unified_mail(f"[BUILD_ERROR][Thorpe_A15] {branch} ({variant}) - Build Failed", msg)
                return False
    else:
        print(f"[INFO] Skipping build phase as requested by --only-test")

    # 2. 觸發測試 (SSH 到 Test Server)
    zip_folder = f"{timestamp}_{branch}_{variant}_a15_gms"
    remote_image_path = f"/media/share/thorpe/Android_15/dailybuild/{zip_folder}/fastboot.zip"
    
    trigger_cmd = (
        f"ssh {TEST_USER}@{TEST_SERVER} 'cd {TEST_DIR} && "
        f"./.venv/bin/python3 trigger_job.py --build {timestamp} --type {variant} --source daily --remote-path {remote_image_path}'"
    )
    
    rc_test = 0
    out_test = ""
    err_test = ""
    
    if dry_run:
        print(f"[DRY-RUN] Would execute: {trigger_cmd}")
    else:
        rc_test, out_test, err_test = run_local(trigger_cmd)

    # 3. 獲取測試結果並產生報告
    status = "UNKNOWN"
    pass_rate = "N/A"
    failed_list = ""
    
    # 根據回傳碼初步判定狀態
    if rc_test != 0:
        if rc_test == 255:
            status = "INFRA_ERROR" # SSH 連線問題
        else:
            status = "TEST_CRITICAL" # 腳本執行中崩潰 (如 OOBE Timeout)
            
        logs = (out_test + err_test).strip().split('\n')
        failed_list = "\nCritical Failure Logs (Tail):\n" + "\n".join([f"!! {l}" for l in logs[-10:]])

    # 嘗試抓取 JSON 摘要以獲得更詳細資訊
    get_json_cmd = f"ssh {TEST_USER}@{TEST_SERVER} 'cat {TEST_DIR}/test_summary.json'"
    if dry_run:
        print(f"[DRY-RUN] Would execute: {get_json_cmd}")
        return True

    rc_json, json_str, _ = run_local(get_json_cmd)
    
    if rc_json == 0:
        try:
            data = json.loads(json_str)
            # 如果 JSON 裡有狀態，則優先使用 JSON 的狀態
            status = data.get('status', status)
            pass_rate = data.get('stats', {}).get('pass_rate', '0%')
            failures = data.get('failed_cases', [])
            if failures:
                # 重新組合失敗清單
                failed_list = "\nFailed Test Cases:\n" + "\n".join([f"- {f['category']} > {f['test_name']}" for f in failures])
            elif status == "SUCCESS":
                failed_list = "All core functional tests passed."
        except Exception as e:
            print(f"[WARN] Failed to parse summary JSON: {e}")
            if status == "UNKNOWN": status = "REPORT_ERROR"

    # 4. 產生並發送郵件
    mail_title = f"[{status}][Thorpe_A15] {branch} ({variant}) - ID: {timestamp}"
    
    # [FIXED] 既然已經不使用 echo -e，我們直接寫正確的反斜線即可，不需要 chr(92) 拼接
    win_path = f"\\\\10.192.188.16\\share\\thorpe\\Android_15\\dailybuild\\{zip_folder}"

    content = f"Thorpe_A15 CI Orchestration Report\n"
    content += "="*60 + "\n"
    content += f"Stage Status:\n"
    content += f"- Overall:   {status}\n"
    content += f"- Pass Rate: {pass_rate}\n\n"
    content += f"Retrieval Link (UNC):\n{win_path}\n\n"
    content += f"Build Details:\n"
    content += f"- Branch:    {branch}\n"
    content += f"- ID:        {timestamp}\n"
    content += f"- Variant:   {variant}\n"
    content += "-"*60 + "\n"
    
    # [FIXED] 修正失敗清單邏輯：如果 Pass Rate 不是 100% 且沒有明確失敗案例，顯示檢查摘要
    if not failed_list or "All core functional tests passed" in failed_list:
        if pass_rate != "100.0%" and pass_rate != "100%":
            content += f"Note: Pass rate is {pass_rate}. Some non-critical items may have failed.\n"
            content += f"Please check the full report in the retrieval link above.\n"
        else:
            content += "All core functional tests passed.\n"
    else:
        content += failed_list + "\n"
        
    content += "="*60 + "\n"
    
    send_unified_mail(mail_title, content)
    return True

def preflight_check():
    """環境相依性預檢 (改良版)"""
    print("\n[PREFLIGHT] Checking environment dependencies...")
    checks = True
    
    # 1. 檢查 Python 版本
    v = sys.version_info
    print(f" - Python version: {v.major}.{v.minor}.{v.micro}", end="")
    if v.major == 3 and v.minor < 7:
        print(f" (Legacy 3.6 detected, using compatibility mode) ... OK")
    else:
        print(f" ... OK")
    
    # 2. 實測 run_local 核心功能 (確保 subprocess 參數在當前環境合法)
    try:
        rc, out, _ = run_local("echo 'engine_check'", capture=True)
        if rc == 0 and "engine_check" in out:
            print(" - Internal execution engine: Verified ... OK")
        else:
            print(f" - Internal execution engine: Returned error (RC:{rc}) ... FAIL")
            checks = False
    except Exception as e:
        print(f" - Internal execution engine: CRASHED ({str(e)}) ... FAIL")
        checks = False

    for cmd in ['ssh', 'mutt']:
        if shutil.which(cmd):
            print(f" - System tool '{cmd}': Found ... OK")
        else:
            # 備選方案：嘗試直接呼叫
            rc, _, _ = run_local(f"{cmd} -V" if cmd == "ssh" else f"{cmd} -v")
            if rc in [0, 1]: 
                print(f" - System tool '{cmd}': Found (via exec) ... OK")
            else:
                print(f" - System tool '{cmd}': NOT FOUND ... FAIL")
                checks = False
            
    if os.path.exists(BUILD_WRAPPER):
        print(f" - Build wrapper '{os.path.basename(BUILD_WRAPPER)}': Found at {BUILD_WRAPPER} ... OK")
    else:
        print(f" - Build wrapper: NOT FOUND ... FAIL")
        print(f"   (Tried: {', '.join(potential_paths)})")
        checks = False

    if checks:
        print("\n[SUCCESS] Preflight passed. You can run with --dry-run to test logic.")
    else:
        print("\n[ERROR] Preflight failed. Please fix the missing dependencies.")
    return checks

def main():
    if "--check" in sys.argv:
        preflight_check()
        sys.exit(0)

    dry_run = "--dry-run" in sys.argv
    only_test = "--only-test" in sys.argv
    
    # 獲取自定義 Timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    if "--timestamp" in sys.argv:
        try:
            ts_idx = sys.argv.index("--timestamp")
            timestamp = sys.argv[ts_idx + 1]
        except IndexError:
            print("[ERROR] --timestamp requires a value.")
            sys.exit(1)

    # 過濾掉非標參數
    ignore_args = ["--dry-run", "--check", "--only-test", "--timestamp", timestamp]
    args = [a for a in sys.argv if a not in ignore_args]

    if len(args) < 3:
        print("Usage: python3 orchestrator.py <BRANCH> <VARIANT> [OPTIONS]")
        print("Options:")
        print("  --dry-run      Print commands without executing")
        print("  --check        Preflight dependency check")
        print("  --only-test    Skip build phase, trigger test only")
        print("  --timestamp ID Override generated timestamp with existing ID")
        sys.exit(1)

    branch = args[1]
    variant_arg = args[2]
    
    if variant_arg == "all":
        process_variant(branch, "userdebug", timestamp, dry_run=dry_run, only_test=only_test)
        process_variant(branch, "user", timestamp, dry_run=dry_run, only_test=only_test)
    else:
        process_variant(branch, variant_arg, timestamp, dry_run=dry_run, only_test=only_test)

if __name__ == "__main__":
    main()
