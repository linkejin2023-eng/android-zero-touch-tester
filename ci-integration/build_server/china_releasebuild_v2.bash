#!/bin/bash
# =================================================================
# china_releasebuild_v2.bash - NoGMS Release CI/CD 調度主控器
# =================================================================

# [測試開關] 若想跳過編譯，請設為 true 進行流程測試
DRY_RUN=false

# [維護重點] 每個新版本 Release 時，請僅修改這兩行：
VERSION="02.01.07.N.260417"
VERSION_DATE="260417"

# [註] 以下兩行需與原始產線腳本 (Template) 內的舊版號一致
OLD_VERSION="02.01.06.N.260310"
OLD_DATE="260310"

# [環境參數] 工具路徑
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_SERVER="10.192.220.17"
IMAGE_SERVER="10.192.188.16"
REMOTE_TEST_USER="franck_lin"
REMOTE_TEST_DIR="/home/franck_lin/auto_test"
IMAGE_ROOT="/media/share/thorpe/Android_15/Release_pega"

# [模板參數] 定義原始編譯腳本名稱 (SCM 提供)
TEMPLATE_USERDEBUG="$SCRIPT_DIR/auto_release_build_nogms_A15.bash"
TEMPLATE_USER="$SCRIPT_DIR/auto_release_userbuild_nogms_A15.bash"

# [通知參數]
MEMBERS="Billy_Chen@pegatroncorp.com,Aaren_Bai@pegatroncorp.com,Nick_Chuang@pegatroncorp.com,Jason1_Pan@pegatroncorp.com,Terry_Tzeng@pegatroncorp.com,Jack2_Hsu@pegatroncorp.com,Franck_Lin@pegatroncorp.com,James8_Chen@pegatroncorp.com,Calvin_Yu@pegatroncorp.com,Smal_Lin@pegatroncorp.com,Frank1_Yen@pegatroncorp.com,Andy1_Hsu@pegatroncorp.com,Hongde_Liu@pegatroncorp.com,Allen2_Chang@pegatroncorp.com,PennyC_Chen@pegatroncorp.com,Gordon1_Yu@pegatroncorp.com,Liche_Wu@pegatroncorp.com,Denny_Yang@pegatroncorp.com,MingChung_Wu@pegatroncorp.com,Hikaru_Fukaya@pegatroncorp.com,Lisa_Hsu@pegatroncorp.com,Rasmus_Lai@pegatroncorp.com,Ryan6_Lin@pegatroncorp.com,Joann_Liu@pegatroncorp.com,Parker6_Chen@pegatroncorp.com,Allen_Lee@pegatroncorp.com,Mike_Yang@pegatroncorp.com,Jeff6_Lin@pegatroncorp.com,Qilin_Zhu@pegatroncorp.com,Parker_Chen@pegatroncorp.com"

# --- 功能函數：從 Worker 腳本中動態提取最新版號 ---
get_release_version() {
    echo "$VERSION"
}

# --- 功能函數：從模板動態提取分支名稱 ---
get_clean_branch() {
    local full_branch=$(grep "^branch=" "$TEMPLATE_USERDEBUG" | cut -d'"' -f2)
    echo "${full_branch#release/}" # 移除 "release/" 前綴以對齊伺服器目錄
}

# --- 功能函數：發送專業級版本通知信 (China Release 版) ---
send_smoke_test_report () {
    local variant=$1
    local version=$2
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

    # [主旨] [STATUS][Project] Release: ID (SKU/Variant) - Smoke Test: RESULT
    local mail_title="$status_tag[Thorpe_A15] Release: REL_$version ($SKU/$variant_cap) - Smoke Test: $status"
    
    # [路徑轉義修正] 針對 China SKU Release 的目錄結構
    local win_root="\\\\\\\\10.192.188.16\\share\\\\thorpe\\\\Android_15\\\\Release_pega"
    local rel_v="REL_${version}"
    local folder_v="${branch}_${variant}_a15_nogms"
    local remote_path="${win_root}\\\\${rel_v}\\\\${folder_v}"

    local content="Thorpe_A15 Smoke Test & Build Notification (China Release)\n"
    content+="============================================================\n\n"
    content+="[Software Retrieval Link]\n"
    content+="${remote_path}\n\n"
    content+="Build Details:\n"
    content+="- Source:   China Release Build\n"
    content+="- Version:  REL_${version}\n"
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
    echo "[V2-INFO] China Release $variant report sent with status: $status"
}

# --- 功能函數：觸發遠端自動化測試 ---
trigger_remote_test () {
    local variant=$1
    local version=$2
    local branch=$3
    echo "[V2-INFO] Triggering China Release test on $TEST_SERVER for $variant ($version)..."
    
    local folder_v="${branch}_${variant}_a15_nogms"
    local remote_path="$IMAGE_ROOT/REL_$version/$folder_v/fastboot.zip"
    
    (
        ssh $REMOTE_TEST_USER@$TEST_SERVER "cd $REMOTE_TEST_DIR && ./.venv/bin/python3 trigger_job.py --build $version --type $variant --source release --sku china --remote-path $remote_path"
        local exit_code=$?
        
        # 抓取測試摘要 JSON
        local summary_json=$(ssh $REMOTE_TEST_USER@$TEST_SERVER "cat $REMOTE_TEST_DIR/test_summary.json")
        
        send_smoke_test_report "$variant" "$version" "$exit_code" "$summary_json" "$branch"
    ) &
}

# =================================================================
# MAIN FLOW
# =================================================================

# 1. 準備編譯腳本 (使用 sed 同時完成：版本替換、路徑修正、全面註解 mail 相關行)
sed "s/$OLD_VERSION/$VERSION/g; s/$OLD_DATE/$VERSION_DATE/g; /mutt/s/^/#/; /mail_title/s/^/#/; /success_content/s/^/#/" $TEMPLATE_USERDEBUG > "$SCRIPT_DIR/auto_release_build_nogms_A15_v2.bash"
sed -i "s/2.2.1/2.2.2/g" "$SCRIPT_DIR/auto_release_build_nogms_A15_v2.bash"

sed "s/$OLD_VERSION/$VERSION/g; s/$OLD_DATE/$VERSION_DATE/g; /mutt/s/^/#/; /mail_title/s/^/#/; /success_content/s/^/#/" $TEMPLATE_USER > "$SCRIPT_DIR/auto_release_userbuild_nogms_A15_v2.bash"
sed -i "s/2.2.1/2.2.2/g" "$SCRIPT_DIR/auto_release_userbuild_nogms_A15_v2.bash"

# 2. 獲取處理後的分支名稱 (從 v2 獲取以確保同步)
VERSION_TAG=$(get_release_version)
BRANCH_TAG=$(get_clean_branch)
echo "[V2-INFO] Detected Target Version: REL_$VERSION_TAG (Branch: $BRANCH_TAG)"

# 3. 執行 China Release Userdebug 編譯
echo "[V2-INFO] Starting China Release Userdebug build..."
if [ "$DRY_RUN" = true ]; then
    echo "[V2-DRYRUN] Skipping Userdebug build..."
else
    bash "$SCRIPT_DIR/auto_release_build_nogms_A15_v2.bash"
fi
trigger_remote_test "userdebug" "$VERSION_TAG" "$BRANCH_TAG"

# 4. 執行 China Release User 編譯
echo "[V2-INFO] Starting China Release User build..."
if [ "$DRY_RUN" = true ]; then
    echo "[V2-DRYRUN] Skipping User build..."
else
    bash "$SCRIPT_DIR/auto_release_userbuild_nogms_A15_v2.bash"
fi
trigger_remote_test "user" "$VERSION_TAG" "$BRANCH_TAG"

echo "[V2-SUCCESS] China Release pipeline execution finished."
wait
echo "[V2-DONE] All China Release tasks completed."
