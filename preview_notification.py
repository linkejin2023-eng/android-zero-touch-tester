import json
import os
from datetime import datetime

def preview_email(json_path):
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found.")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 基礎解析
    status = data.get('status', 'UNKNOWN')
    pass_rate = data.get('stats', {}).get('pass_rate', 'N/A')
    version = data.get('version', 'Unknown_Version')
    variant = data.get('variant', 'user').lower()
    exempt_count = data.get('stats', {}).get('exempt', 0)
    
    # --- 智慧模式判定 ---
    is_release = version.startswith("REL_")
    is_china = (".N." in version) or ("nogms" in version) or ("NoGMS" in version)
    
    # 決定 SKU 與標籤
    sku = "China" if is_china else "GMS"
    
    if is_china:
        source_label = "China Release Build" if is_release else "China Daily Build"
        header_label = "(China Release)" if is_release else "(China SKU)"
    else:
        source_label = "Release Build" if is_release else "Daily Build"
        header_label = "(RELEASE)" if is_release else ""

    # 1. 模擬主旨決定邏輯
    status_tag = f"[{status}]"
    if status == "INFRA_ERROR":
        status_tag = f"[CRITICAL: {status}]"
    elif status == "SUCCESS":
        if exempt_count > 0:
            status_tag = "[SUCCESS (Exempted)]"
    
    mode_str = "Release" if is_release else "Daily Build"
    mail_title = f"{status_tag}[Thorpe_A15] {mode_str}: {version} ({sku}/{variant.capitalize()}) - Smoke Test: {status}"

    # 2. 模擬內文渲染邏輯 (對齊 Bash 腳本中的 win_root 與路徑拼接)
    content = f"Thorpe_A15 Smoke Test & Build Notification {header_label}\n"
    content += "============================================================\n\n"
    content += "[Software Retrieval Link]\n"
    
    # 模擬四種路徑拼接規則
    win_base = "\\\\\\\\10.192.188.16\\share\\thorpe\\Android_15\\"
    if is_release:
        if is_china:
            # China Release: ...\Release_pega\REL_version\branch_variant_a15_nogms
            content += f"{win_base}Release_pega\\\\{version}\\\\branch_{variant}_a15_nogms\n\n"
        else:
            # GMS Release: ...\Release_pega\version\variant
            content += f"{win_base}Release_pega\\\\{version}\\\\{variant}\n\n"
    else:
        if is_china:
            # China Daily: ...\dailybuild\timestamp_branch_variant_a15_nogms
            content += f"{win_base}dailybuild\\\\{version}_branch_{variant}_a15_nogms\n\n"
        else:
            # GMS Daily: ...\dailybuild\timestamp_thorpe_dev_variant_a15_gms
            content += f"{win_base}dailybuild\\\\{version}_thorpe_dev_{variant}_a15_gms\n\n"

    content += "Build Details:\n"
    content += f"- Source:   {source_label}\n"
    if is_release:
        content += f"- Version:  {version}\n"
    else:
        content += f"- Ident:    {version}\n"
    content += f"- SKU:      {sku}\n"
    content += f"- Variant:  {variant.capitalize()}\n\n"
    content += f"Smoke Test Status: {status} (Pass Rate: {pass_rate})\n"
    content += "------------------------------------------------------------\n"
    
    failed_list = "\n".join([f"- {c['category']} > {c['test_name']}" for c in data.get('failed_cases', [])])
    if failed_list:
        content += f"Critical Failures:\n{failed_list}\n\n"
    
    env_list = "\n".join([f"- {c['category']} > {c['test_name']}" for c in data.get('env_excluded_cases', [])])
    if env_list:
        content += f"Environmental Exclusions:\n{env_list}\n"
        content += "Note: These items are excluded from overall status due to environment.\n"
    
    if status == "SUCCESS":
        content += "Note: This version has passed all core functional tests.\n"
    
    content += "============================================================\n"

    # 輸出結果
    print("\n" + "="*20 + " SMART EMAIL PREVIEW " + "="*20)
    print(f"Detected Mode: {'CHINA' if is_china else 'GMS'} | {'RELEASE' if is_release else 'DAILY'}")
    print(f"SUBJECT: {mail_title}")
    print("-" * 55)
    print(content)
    print("="*55 + "\n")

    # 存檔
    output_file = "email_preview.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"SUBJECT: {mail_title}\n")
        f.write("-" * 55 + "\n")
        f.write(content)
    print(f"Preview saved to: {output_file}")

if __name__ == "__main__":
    preview_email("test_summary.json")
