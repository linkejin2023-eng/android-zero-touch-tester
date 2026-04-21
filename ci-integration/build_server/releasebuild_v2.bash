#!/bin/bash
# =================================================================
# releasebuild_v2.bash - CI/CD 自動化整合版 (Non-Invasive)
# =================================================================

# [測試開關] 若想跳過 4-5 小時編譯，請設為 true 進行流程測試
DRY_RUN=false

# [維護重點] 每個新版本 Build 時，請僅修改這兩行：
VERSION="02.02.03.260418"
VERSION_DATE="2026-04-18"

# [註] 除非原始範本 (.bash 檔) 內的版本號被 SCM 手動更改了，否則以下兩行不需變動
OLD_VERSION="02.02.01.260331"
OLD_DATE="2026-03-31"

TEST_SERVER="10.192.220.17"
IMAGE_SERVER="10.192.188.16"
REMOTE_USER="nick_chuang"     # Image Server User
PASSWORD="32600"
REMOTE_TEST_USER="franck_lin"   # Test Server User

# [SoT 參數] 定義 Image Server 上的路徑根目錄
REMOTE_RELEASE_ROOT="/media/share/thorpe/Android_15/Release_pega"

# [環境參數] 定義工具路徑
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# [環境參數] 定義測試機與本地 Server 的工作目錄
REMOTE_TEST_DIR="/home/franck_lin/auto_test"
LOCAL_BIN_DIR="/home/server/bin"
LOCAL_ARTIFACT_DIR="$SCRIPT_DIR/A15_artifact"
SCM_BUILD_DIR="/home/server/thorpe_dailybuild_A15/shell-script"

# [模板參數] 定義原始編譯腳本名稱 (SCM 提供)
TEMPLATE_USERDEBUG="$SCRIPT_DIR/auto_release_build_A15.bash"
TEMPLATE_USER="$SCRIPT_DIR/auto_release_userbuild_A15.bash"

# --- 功能函數：同步上傳 Build Info ---
upload_json_to_server () {
    local variant=$1
    echo "[V2-INFO] Syncing build_info.json for $variant..."
    
    pushd "$LOCAL_BIN_DIR" > /dev/null
    sed "s/$OLD_VERSION/$VERSION/g" build_info.json > build_info_tmp.json
    sed -i "s/$OLD_DATE/$VERSION_DATE/g" build_info_tmp.json
    
    # 執行上傳 (使用變數化路徑)
    expect -c "
        set timeout 300
        spawn scp build_info_tmp.json $REMOTE_USER@$IMAGE_SERVER:$REMOTE_RELEASE_ROOT/REL_$VERSION/$variant/build_info.json
        expect \"password:\"
        send \"${PASSWORD}\r\"
        expect eof"
    
    popd > /dev/null
}

# [通知參數]
MEMBERS="Billy_Chen@pegatroncorp.com,Aaren_Bai@pegatroncorp.com,Nick_Chuang@pegatroncorp.com,Jason1_Pan@pegatroncorp.com,Terry_Tzeng@pegatroncorp.com,Jack2_Hsu@pegatroncorp.com,Franck_Lin@pegatroncorp.com,James8_Chen@pegatroncorp.com,Calvin_Yu@pegatroncorp.com,Smal_Lin@pegatroncorp.com,Frank1_Yen@pegatroncorp.com,Andy1_Hsu@pegatroncorp.com,Hongde_Liu@pegatroncorp.com,Allen2_Chang@pegatroncorp.com,PennyC_Chen@pegatroncorp.com,Gordon1_Yu@pegatroncorp.com,Liche_Wu@pegatroncorp.com,Denny_Yang@pegatroncorp.com,MingChung_Wu@pegatroncorp.com,Lisa_Hsu@pegatroncorp.com,Rasmus_Lai@pegatroncorp.com,Ryan6_Lin@pegatroncorp.com,Joann_Liu@pegatroncorp.com,Parker6_Chen@pegatroncorp.com,Allen_Lee@pegatroncorp.com,Mike_Yang@pegatroncorp.com,Jeff6_Lin@pegatroncorp.com,Qilin_Zhu@pegatroncorp.com,Parker_Chen@pegatroncorp.com"

# --- 功能函數：發送專業級版本通知信 (Release 版) ---
send_smoke_test_report () {
    local variant=$1
    local version=$2
    local code=$3
    local json_data="$4"
    local SKU="GMS"
    
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
    
    local win_root="\\\\\\\\10.192.188.16\\share\\\\thorpe\\\\Android_15\\\\Release_pega"
    local remote_path="${win_root}\\\\REL_${version}\\\\${variant}"

    local content="Thorpe_A15 Smoke Test & Build Notification (RELEASE)\n"
    content+="============================================================\n\n"
    content+="[Software Retrieval Link]\n"
    content+="${remote_path}\n\n"
    content+="Build Details:\n"
    content+="- Source:   Release Build\n"
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
    echo "[V2-INFO] $variant Release report sent with status: $status"
}

# --- 功能函數：觸發遠端自動化測試 ---
trigger_remote_test () {
    local variant=$1
    echo "[V2-INFO] Triggering automated test on $TEST_SERVER for $variant..."
    
    local remote_path="$REMOTE_RELEASE_ROOT/REL_$VERSION/$variant/fastboot.zip"
    
    local extra_flags=""
    if [ "$DRY_RUN" = true ]; then
        extra_flags="--check-only"
    fi

    # 異步執行測試，並在結束後立刻發信
    (
        ssh $REMOTE_TEST_USER@$TEST_SERVER "cd $REMOTE_TEST_DIR && ./.venv/bin/python3 trigger_job.py --build $VERSION --type $variant --source release $extra_flags --remote-path $remote_path"
        local exit_code=$?
        
        # 抓取測試摘要 JSON
        local summary_json=$(ssh $REMOTE_TEST_USER@$TEST_SERVER "cat $REMOTE_TEST_DIR/test_summary.json")
        
        send_smoke_test_report "$variant" "$VERSION" "$exit_code" "$summary_json"
    ) &
}

# =================================================================
# MAIN FLOW - 正式編譯流程
# =================================================================

# 1. 準備編譯腳本 (使用變數化的模板名稱)
# 這裡使用 sed 同時完成：1.版號替換 2.日期替換 3.全面註解 mail 相關行 (mutt, mail_title, success_content)
sed "s/$OLD_VERSION/$VERSION/g; s/$OLD_DATE/$VERSION_DATE/g; /mutt/s/^/#/; /mail_title/s/^/#/; /success_content/s/^/#/" $TEMPLATE_USERDEBUG > "$SCRIPT_DIR/auto_release_build_A15_v2.bash"
sed -i "s/2.2.1/2.2.2/g" "$SCRIPT_DIR/auto_release_build_A15_v2.bash"

sed "s/$OLD_VERSION/$VERSION/g; s/$OLD_DATE/$VERSION_DATE/g; /mutt/s/^/#/; /mail_title/s/^/#/; /success_content/s/^/#/" $TEMPLATE_USER > "$SCRIPT_DIR/auto_release_userbuild_A15_v2.bash"
sed -i "s/2.2.1/2.2.2/g" "$SCRIPT_DIR/auto_release_userbuild_A15_v2.bash"

# 2. 執行 Userdebug 編譯
if [ "$DRY_RUN" = true ]; then
    echo "[V2-DRYRUN] Skipping Userdebug build (Simulated)..."
    sleep 2
else
    echo "[V1-ORIGIN] Starting Userdebug build..."
    rm -rf $LOCAL_ARTIFACT_DIR/artifact/
    bash "$SCRIPT_DIR/auto_release_build_A15_v2.bash"
    mv $SCM_BUILD_DIR/artifact $LOCAL_ARTIFACT_DIR/
fi

# 3. [V2 插入] Userdebug 完工 -> 上傳 JSON -> 觸發測試
upload_json_to_server "userdebug"
trigger_remote_test "userdebug"

# 4. 執行 User 編譯
if [ "$DRY_RUN" = true ]; then
    echo "[V2-DRYRUN] Skipping User build (Simulated)..."
    sleep 2
else
    echo "[V1-ORIGIN] Starting User build..."
    bash "$SCRIPT_DIR/auto_release_userbuild_A15_v2.bash"
fi

# 5. [V2 插入] User 完工 -> 上傳 JSON -> 觸發測試
upload_json_to_server "user"
trigger_remote_test "user"

echo "[V2-SUCCESS] Pipeline execution finished (DRY_RUN=$DRY_RUN)."
wait # 等待背景任務結束以確保游標正常歸還
