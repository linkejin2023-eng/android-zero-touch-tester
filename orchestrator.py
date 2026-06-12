#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
orchestrator.py - 統一主控器 (Unified Orchestrator) v3
架構：Config-Driven (ci_config.json)
能力：支援多 SKU (GMS/China) 與多 Source (Daily/Release)，動態驅動 Build Server 與 Test Server。
"""

import os
import sys
import json
import argparse
import subprocess
import shutil
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "ci_config.json")

def load_config():
    if not os.path.exists(CONFIG_PATH):
        print(f"[ERROR] Config file missing: {CONFIG_PATH}")
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def run_local(cmd, capture=True):
    """執行本地指令並捕捉輸出"""
    print(f"[EXEC] {cmd}")
    try:
        if capture:
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
    """透過系統 mutt 指令發信"""
    print(f"[MAIL] Sending: {subject}")
    # 收件人預設寫死在發信函式內或可日後移入 JSON
    recipients = "Nick_Chuang@pegatroncorp.com,Billy_Chen@pegatroncorp.com,Franck_Lin@pegatroncorp.com"
    recipient_list = [r.strip() for r in recipients.split(',')]
    try:
        cmd = ["mutt", "-s", subject, "--"] + recipient_list
        subprocess.run(cmd, input=content, universal_newlines=True, check=True)
    except Exception as e:
        print(f"[ERROR] Failed to send mail via mutt: {e}")
        print("--- FALLBACK MAIL CONTENT ---")
        print(f"Subject: {subject}")
        print(content)
        print("------------------------------")

def process_variant(branch, variant, build_id, sku, source, config, dry_run=False, only_test=False):
    """處理單一 Variant 的完整生命週期：編譯 -> 測試 -> 發信"""
    mode_str = f"[DRY-RUN]" if dry_run else ""
    if only_test: mode_str += " [ONLY-TEST]"
    print(f"\n{'='*70}\n>>> Processing {branch} ({variant}) SKU:{sku} Source:{source} ID:{build_id} {mode_str}\n{'='*70}")

    # 解析設定檔
    build_conf = config["build_servers"].get(sku)
    if not build_conf:
        print(f"[ERROR] Build config for SKU '{sku}' not found in ci_config.json")
        return False
    
    workspace = build_conf["codebase_paths"].get(source)
    if not workspace:
        print(f"[ERROR] Workspace for source '{source}' not found in ci_config.json")
        return False

    test_conf = config["test_server"]
    img_conf = config["image_server"]

    # ========================================================
    # 1. 執行遠端編譯 (SSH to Build Server)
    # ========================================================
    if not only_test:
        build_cmd = (
            f"ssh {build_conf['user']}@{build_conf['ip']} "
            f"\"bash {build_conf['script_path']} {branch} {variant} {build_id} {sku} {source} {workspace}\""
        )
        if dry_run:
            print(f"[DRY-RUN] Would execute Build Command:\n{build_cmd}")
        else:
            rc, stdout, stderr = run_local(build_cmd, capture=False)
            if rc != 0:
                msg = f"Stage: Build Process\nResult: Failed (RC: {rc})\n\nPlease check Build Server Logs."
                send_unified_mail(f"[BUILD_ERROR][Thorpe_A15] {branch} ({variant}) - Build Failed", msg)
                return False
    else:
        print(f"[INFO] Skipping build phase as requested by --only-test")

    # ========================================================
    # 2. 觸發遠端測試 (SSH to Test Server)
    # ========================================================
    zip_folder = f"{build_id}_{branch}_{variant}_a15_{sku}"
    
    # 動態決定 Image Server 路徑
    if source == "release":
        remote_image_path = f"{img_conf['linux_base_path']}/Release_pega/REL_{build_id}/{variant}/fastboot.zip"
        win_path = f"{img_conf['win_base_path']}\\Release_pega\\REL_{build_id}\\{variant}"
    else:
        remote_image_path = f"{img_conf['linux_base_path']}/dailybuild/{zip_folder}/fastboot.zip"
        win_path = f"{img_conf['win_base_path']}\\dailybuild\\{zip_folder}"

    trigger_cmd = (
        f"ssh {test_conf['user']}@{test_conf['ip']} 'rm -f {test_conf['script_path']}/test_summary.json && "
        f"cd {test_conf['script_path']} && "
        f"./.venv/bin/python3 trigger_job.py --build {build_id} --type {variant} --source {source} --remote-path {remote_image_path}'"
    )
    
    rc_test = 0
    if dry_run:
        print(f"[DRY-RUN] Would execute Test Command:\n{trigger_cmd}")
    else:
        rc_test, out_test, err_test = run_local(trigger_cmd)

    # ========================================================
    # 3. 獲取測試結果
    # ========================================================
    status = "UNKNOWN"
    pass_rate = "N/A"
    failed_list = ""
    
    if rc_test != 0:
        if rc_test == 255:
            status = "INFRA_ERROR"
        else:
            status = "TEST_CRITICAL"
        failed_list = "Critical Error occurred during test triggering or execution."

    get_json_cmd = f"ssh {test_conf['user']}@{test_conf['ip']} 'cat {test_conf['script_path']}/test_summary.json'"
    
    if dry_run:
        print(f"[DRY-RUN] Would fetch JSON:\n{get_json_cmd}")
        return True

    rc_json, json_str, _ = run_local(get_json_cmd)
    
    if rc_json == 0 and json_str.strip():
        try:
            data = json.loads(json_str)
            status = data.get('status', status)
            pass_rate = data.get('stats', {}).get('pass_rate', '0%')
            failures = data.get('failed_cases', [])
            if failures:
                failed_list = "\nFailed Test Cases:\n" + "\n".join([f"- {f['category']} > {f['test_name']}" for f in failures])
            elif status == "SUCCESS":
                failed_list = "All core functional tests passed."
        except Exception as e:
            print(f"[WARN] Failed to parse summary JSON: {e}")
            if status == "UNKNOWN": status = "REPORT_ERROR"

    # ========================================================
    # 4. 產生並發送統一郵件
    # ========================================================
    subject_status = f"[CRITICAL: {status}]" if "ERROR" in status or "CRITICAL" in status else f"[{status}]"
    mail_title = f"{subject_status}[Thorpe_A15] {source.capitalize()} Build ({sku.upper()}/{variant.capitalize()}) - ID: {build_id}"

    content = f"Thorpe_A15 CI Orchestration Report\n"
    content += "="*60 + "\n"
    content += f"Stage Status:\n"
    content += f"- Overall:   {status}\n"
    content += f"- Pass Rate: {pass_rate}\n\n"
    content += f"Retrieval Link (UNC):\n{win_path}\n\n"
    content += f"Build Details:\n"
    content += f"- Branch:    {branch}\n"
    content += f"- SKU:       {sku.upper()}\n"
    content += f"- Source:    {source.capitalize()}\n"
    content += f"- ID:        {build_id}\n"
    content += f"- Variant:   {variant.capitalize()}\n"
    content += "-"*60 + "\n"
    
    if not failed_list or "All core functional tests passed" in failed_list:
        if pass_rate != "100.0%" and pass_rate != "100%":
            content += f"Note: Pass rate is {pass_rate}. Some non-critical items may have failed.\n"
        else:
            content += "All core functional tests passed.\n"
    else:
        content += failed_list + "\n"
        
    content += "="*60 + "\n"
    
    send_unified_mail(mail_title, content)
    return True

def main():
    parser = argparse.ArgumentParser(description="Thorpe Unified Orchestrator")
    parser.add_argument("branch", help="Target branch name")
    parser.add_argument("variant", choices=["userdebug", "user", "all"], help="Build variant")
    parser.add_argument("--sku", choices=["gms", "china"], default="gms", help="SKU selection")
    parser.add_argument("--source", choices=["daily", "release"], default="daily", help="Source pipeline type")
    parser.add_argument("--version", help="Release version (e.g. 02.02.01). Required if source is release.")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing")
    parser.add_argument("--only-test", action="store_true", help="Skip build phase, trigger test only")
    args = parser.parse_args()

    config = load_config()

    # 合成 Build ID
    if args.source == "release":
        if not args.version:
            print("[ERROR] --version is required for release builds!")
            sys.exit(1)
        date_str = datetime.now().strftime("%y%m%d") # e.g. 260527
        build_id = f"{args.version}.{date_str}"
    else:
        build_id = datetime.now().strftime("%Y%m%d%H%M") # e.g. 202605271030

    # 執行流程
    if args.variant == "all":
        process_variant(args.branch, "userdebug", build_id, args.sku, args.source, config, args.dry_run, args.only_test)
        process_variant(args.branch, "user", build_id, args.sku, args.source, config, args.dry_run, args.only_test)
    else:
        process_variant(args.branch, args.variant, build_id, args.sku, args.source, config, args.dry_run, args.only_test)

if __name__ == "__main__":
    main()
