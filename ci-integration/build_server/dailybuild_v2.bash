#!/bin/bash
# =================================================================
# dailybuild_v2.bash - Daily Build 自動化整合版 (Non-Invasive)
# =================================================================

# [測試開關] 若想跳過編譯，請設為 true 進行流程測試
DRY_RUN=false

TEST_SERVER="10.192.220.17"
IMAGE_SERVER="10.192.188.16"
REMOTE_USER="nick_chuang"     # Image Server User
PASSWORD="32600"
REMOTE_TEST_USER="franck_lin"   # Test Server User

# [通知參數]
MEMBERS="Billy_Chen@pegatroncorp.com,Aaren_Bai@pegatroncorp.com,Nick_Chuang@pegatroncorp.com,Jason1_Pan@pegatroncorp.com,Terry_Tzeng@pegatroncorp.com,Jack2_Hsu@pegatroncorp.com,Franck_Lin@pegatroncorp.com,James8_Chen@pegatroncorp.com,Calvin_Yu@pegatroncorp.com,Smal_Lin@pegatroncorp.com,Frank1_Yen@pegatroncorp.com,Andy1_Hsu@pegatroncorp.com,Hongde_Liu@pegatroncorp.com,Allen2_Chang@pegatroncorp.com,PennyC_Chen@pegatroncorp.com,Gordon1_Yu@pegatroncorp.com,Liche_Wu@pegatroncorp.com,Denny_Yang@pegatroncorp.com,MingChung_Wu@pegatroncorp.com,Lisa_Hsu@pegatroncorp.com,Rasmus_Lai@pegatroncorp.com,Ryan6_Lin@pegatroncorp.com,Joann_Liu@pegatroncorp.com,Parker6_Chen@pegatroncorp.com,Allen_Lee@pegatroncorp.com,Mike_Yang@pegatroncorp.com,Jeff6_Lin@pegatroncorp.com,Qilin_Zhu@pegatroncorp.com,Parker_Chen@pegatroncorp.com"
# MEMBERS="Nick_Chuang@pegatroncorp.com"

# [SoT 參數] 定義 Image Server 上的路徑根目錄
REMOTE_DAILY_ROOT="/media/share/thorpe/Android_15/dailybuild"

# [環境參數] 定義工具路徑
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REMOTE_TEST_DIR="/home/franck_lin/auto_test"
LOCAL_ARTIFACT_DIR="$SCRIPT_DIR/A15_artifact"
SCM_BUILD_DIR="/home/server/thorpe_dailybuild_A15/shell-script"

# [防呆] 啟動前先清理舊的殘留時間戳，避免編譯失敗時誤讀舊資料
rm -f "$SCRIPT_DIR"/last_builtdate_*.tmp

# [子腳本參數]
SUB_USERDEBUG="auto_daily_build_A15_v2.bash"
SUB_USER="auto_daily_userbuild_A15_v2.bash"

# --- 功能函數：發送專業級版本通知信 ---
send_smoke_test_report () {
    local variant=$1
    local timestamp=$2
    local code=$3
    local json_data="$4"
    local SKU="GMS"
    
    # 解析 JSON 數據 (使用 python 作為可靠解析器)
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

    # [主旨] [STATUS][Project] Activity: ID (SKU/Variant) - Smoke Test: RESULT
    local mail_title="$status_tag[Thorpe_A15] Daily Build: $timestamp ($SKU/$variant_cap) - Smoke Test: $status"
    
    local win_root="\\\\\\\\10.192.188.16\\share\\\\thorpe\\\\Android_15\\\\dailybuild"
    local remote_path="${win_root}\\\\${timestamp}_thorpe_dev_${variant}_a15_gms"

    local content="Thorpe_A15 Smoke Test & Build Notification\n"
    content+="============================================================\n\n"
    content+="[Software Retrieval Link]\n"
    content+="${remote_path}\n\n"
    content+="Build Details:\n"
    content+="- Source:   Daily Build\n"
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
    echo "[V2-INFO] $variant report sent with status: $status"
}

# --- 功能函數：觸發遠端自動化測試 ---
trigger_remote_test () {
    local variant=$1
    local built_date=$2
    
    echo "[V2-INFO] Triggering automated test on $TEST_SERVER for daily $variant ($built_date)..."
    
    local zipfile="${built_date}_thorpe_dev_${variant}_a15_gms"
    local remote_path="${REMOTE_DAILY_ROOT}/${zipfile}/fastboot.zip"
    
    local extra_flags=""
    if [ "$DRY_RUN" = true ]; then
        extra_flags="--check-only"
    fi

    # 異步執行測試，並在結束後立刻發信
    (
        ssh $REMOTE_TEST_USER@$TEST_SERVER "cd $REMOTE_TEST_DIR && ./.venv/bin/python3 trigger_job.py --build $built_date --type $variant --source daily $extra_flags --remote-path $remote_path"
        local exit_code=$?
        
        # 抓取測試摘要 JSON
        local summary_json=$(ssh $REMOTE_TEST_USER@$TEST_SERVER "cat $REMOTE_TEST_DIR/test_summary.json")
        
        send_smoke_test_report "$variant" "$built_date" "$exit_code" "$summary_json"
    ) &
}

# =================================================================
# MAIN FLOW - 正式編譯流程
# =================================================================

# 1. 執行 Userdebug 編譯
echo "[V2-INFO] Starting Daily Userdebug build..."
if [ "$DRY_RUN" = true ]; then
    echo "[V2-DRYRUN] Skipping Userdebug build (Simulated)..."
    # 模擬產出時間戳
    echo "$(date +%Y%m%d%H%M)" > "$SCRIPT_DIR/last_builtdate_userdebug.tmp"
    sleep 2
else
    rm -rf "$LOCAL_ARTIFACT_DIR/artifact/"
    bash "$SCRIPT_DIR/$SUB_USERDEBUG"
    # 將產出物搬移至 A15_artifact 以供後續 Jenkins 收集 (承襲 V1 邏輯)
    mv "$SCM_BUILD_DIR/artifact" "$LOCAL_ARTIFACT_DIR/"
fi

# 2. 獲取日期並觸發測試
if [ -f "$SCRIPT_DIR/last_builtdate_userdebug.tmp" ]; then
    DATE_DEBUG=$(cat "$SCRIPT_DIR/last_builtdate_userdebug.tmp")
    rm -f "$SCRIPT_DIR/last_builtdate_userdebug.tmp" # 讀完即刪
    trigger_remote_test "userdebug" "$DATE_DEBUG"
else
    echo "[V2-ERROR] Could not find userdebug timestamp file. Trigger failed."
fi

# 3. 執行 User 編譯
echo "[V2-INFO] Starting Daily User build..."
if [ "$DRY_RUN" = true ]; then
    echo "[V2-DRYRUN] Skipping User build (Simulated)..."
    echo "$(date +%Y%m%d%H%M)" > "$SCRIPT_DIR/last_builtdate_user.tmp"
    sleep 2
else
    bash "$SCRIPT_DIR/$SUB_USER"
fi

# 4. 獲取日期並觸發測試
if [ -f "$SCRIPT_DIR/last_builtdate_user.tmp" ]; then
    DATE_USER=$(cat "$SCRIPT_DIR/last_builtdate_user.tmp")
    rm -f "$SCRIPT_DIR/last_builtdate_user.tmp" # 讀完即刪
    trigger_remote_test "user" "$DATE_USER"
else
    echo "[V2-ERROR] Could not find user timestamp file. Trigger failed."
fi

echo "[V2-SUCCESS] Daily build pipeline execution finished."
echo "[V2-INFO] Waiting for all background tests to sync results..."
wait # 等待背景任務結束
echo "[V2-DONE] All daily build tasks completed."
