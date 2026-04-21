#!/bin/bash
# =================================================================
# china_dailybuild_v2.bash - NoGMS Daily CI/CD 調度主控器
# =================================================================

# [環境參數] 工具路徑
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_SERVER="10.192.220.17"
IMAGE_SERVER="10.192.188.16"
REMOTE_TEST_USER="franck_lin"
REMOTE_TEST_DIR="/home/franck_lin/auto_test"
IMAGE_ROOT="/media/share/thorpe/Android_15/dailybuild"

# [通知參數] 包含 China/NoGMS 團隊成員
MEMBERS="Billy_Chen@pegatroncorp.com,Aaren_Bai@pegatroncorp.com,Nick_Chuang@pegatroncorp.com,Jason1_Pan@pegatroncorp.com,Terry_Tzeng@pegatroncorp.com,Jack2_Hsu@pegatroncorp.com,Franck_Lin@pegatroncorp.com,James8_Chen@pegatroncorp.com,Calvin_Yu@pegatroncorp.com,Smal_Lin@pegatroncorp.com,Frank1_Yen@pegatroncorp.com,Andy1_Hsu@pegatroncorp.com,Hongde_Liu@pegatroncorp.com,Allen2_Chang@pegatroncorp.com,PennyC_Chen@pegatroncorp.com,Gordon1_Yu@pegatroncorp.com,Liche_Wu@pegatroncorp.com,Denny_Yang@pegatroncorp.com,MingChung_Wu@pegatroncorp.com,Hikaru_Fukaya@pegatroncorp.com,Lisa_Hsu@pegatroncorp.com,Rasmus_Lai@pegatroncorp.com,Ryan6_Lin@pegatroncorp.com,Joann_Liu@pegatroncorp.com,Parker6_Chen@pegatroncorp.com,Allen_Lee@pegatroncorp.com,Mike_Yang@pegatroncorp.com,Jeff6_Lin@pegatroncorp.com,Qilin_Zhu@pegatroncorp.com,Parker_Chen@pegatroncorp.com"

# --- 功能函數：從 Worker 腳本中動態提取分支名稱 ---
get_branch_name() {
    local script=$1
    grep "^branch=" "$SCRIPT_DIR/$script" | cut -d'"' -f2
}

# --- 功能函數：發送專業級版本通知信 (China 版) ---
send_smoke_test_report () {
    local variant=$1
    local timestamp=$2
    local code=$3
    local json_data="$4"
    local branch=$5
    local SKU="China"
    
    # 解析 JSON 數據
    local status=$(echo "$json_data" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'UNKNOWN'))")
    local pass_rate=$(echo "$json_data" | python3 -c "import sys, json; print(json.load(sys.stdin).get('stats', {}).get('pass_rate', 'N/A'))")
    local failed_list=$(echo "$json_data" | python3 -c "import sys, json; data=json.load(sys.stdin); print('\n'.join([f'- {c[\"category\"]} > {c[\"test_name\"]}' for c in data.get('failed_cases', [])]))")
    local env_list=$(echo "$json_data" | python3 -c "import sys, json; data=json.load(sys.stdin); print('\n'.join([f'- {c[\"category\"]} > {c[\"test_name\"]}' for c in data.get('env_excluded_cases', [])]))")

    # 決定主旨狀態標籤
    local status_tag="[$status]"
    if [ "$status" == "INFRA_ERROR" ]; then
        status_tag="[CRITICAL: $status]"
    elif [ "$status" == "SUCCESS" ]; then
        # 檢查是否有豁免項目
        local exempt_count=$(echo "$json_data" | python3 -c "import sys, json; print(json.load(sys.stdin).get('stats', {}).get('exempt', 0))")
        if [ "$exempt_count" -gt 0 ]; then
            status_tag="[SUCCESS (Exempted)]"
        fi
    fi
    local variant_cap="User"
    [ "$variant" == "userdebug" ] && variant_cap="Userdebug"

    # [主旨] [STATUS][Project] Daily Build: ID (SKU/Variant) - Smoke Test: RESULT
    local mail_title="$status_tag[Thorpe_A15] Daily Build: $timestamp ($SKU/$variant_cap) - Smoke Test: $status"
    
    local win_root="\\\\\\\\10.192.188.16\\share\\\\thorpe\\\\Android_15\\\\dailybuild"
    local remote_path="${win_root}\\\\${timestamp}_${branch}_${variant}_a15_nogms"

    local content="Thorpe_A15 Smoke Test & Build Notification (China SKU)\n"
    content+="============================================================\n\n"
    content+="[Software Retrieval Link]\n"
    content+="${remote_path}\n\n"
    content+="Build Details:\n"
    content+="- Source:   China Daily Build\n"
    content+="- Ident:    ${timestamp}\n"
    content+="- SKU:      ${SKU}\n"
    content+="- Variant:  ${variant_cap}\n\n"
    content+="Smoke Test Status: ${status} (Pass Rate: ${pass_rate})\n"
    content+="------------------------------------------------------------\n"
    
    if [ ! -z "$failed_list" ]; then
        content+="Critical Failures:\n${failed_list}\n\n"
    fi
    
    if [ ! -z "$env_list" ]; then
        content+="Environmental Exclusions:\n${env_list}\n"
        content+="Note: These items are excluded from overall status due to environment.\n"
    fi
    
    if [ "$status" == "SUCCESS" ]; then
        content+="Note: This version has passed all core functional tests.\n"
    fi
    content+="============================================================\n"
    
    echo -e "$content" | mutt -s "$mail_title" -- "$MEMBERS"
    echo "[V2-INFO] China $variant report sent with status: $status"
}

# --- 功能函數：觸發遠端自動化測試 ---
trigger_remote_test () {
    local variant=$1
    local timestamp=$2
    local branch=$3
    echo "[V2-INFO] Triggering China automated test on $TEST_SERVER for $variant ($timestamp)..."
    
    local remote_path="$IMAGE_ROOT/${timestamp}_${branch}_${variant}_a15_nogms/fastboot.zip"
    
    (
        ssh $REMOTE_TEST_USER@$TEST_SERVER "cd $REMOTE_TEST_DIR && ./.venv/bin/python3 trigger_job.py --build $timestamp --type $variant --source daily --sku china --remote-path $remote_path"
        local exit_code=$?
        
        # 抓取測試摘要 JSON
        local summary_json=$(ssh $REMOTE_TEST_USER@$TEST_SERVER "cat $REMOTE_TEST_DIR/test_summary.json")
        
        send_smoke_test_report "$variant" "$timestamp" "$exit_code" "$summary_json" "$branch"
    ) &
}

# =================================================================
# MAIN FLOW - 正式編譯流程
# =================================================================
export DATE_TAG=$(date +%Y%m%d%H%M)

# 1. 執行 China Userdebug 編譯
BRANCH_USERDEBUG=$(get_branch_name "auto_daily_build_nogms_A15_v2.bash")
echo "[V2-INFO] Starting China Userdebug build (Branch: $BRANCH_USERDEBUG, Timestamp: $DATE_TAG)..."
bash "$SCRIPT_DIR/auto_daily_build_nogms_A15_v2.bash"
trigger_remote_test "userdebug" "$DATE_TAG" "$BRANCH_USERDEBUG"

# 2. 執行 China User 編譯
BRANCH_USER=$(get_branch_name "auto_daily_userbuild_nogms_A15_v2.bash")
echo "[V2-INFO] Starting China User build (Branch: $BRANCH_USER, Timestamp: $DATE_TAG)..."
bash "$SCRIPT_DIR/auto_daily_userbuild_nogms_A15_v2.bash"
trigger_remote_test "user" "$DATE_TAG" "$BRANCH_USER"

echo "[V2-SUCCESS] China Daily build pipeline execution finished."
wait # 等待背景任務結束
echo "[V2-DONE] All China tasks completed."
