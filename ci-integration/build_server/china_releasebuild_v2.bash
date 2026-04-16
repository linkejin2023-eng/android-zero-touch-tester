#!/bin/bash
# =================================================================
# china_releasebuild_v2.bash - NoGMS Release CI/CD 調度主控器
# =================================================================

# [環境參數] 工具路徑
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_SERVER="10.192.220.17"
IMAGE_SERVER="10.192.188.16"
REMOTE_TEST_USER="franck_lin"
REMOTE_TEST_DIR="/home/franck_lin/auto_test"
IMAGE_ROOT="/media/share/thorpe/Android_15/Release_pega"

# [通知參數]
MEMBERS="Billy_Chen@pegatroncorp.com,Aaren_Bai@pegatroncorp.com,Nick_Chuang@pegatroncorp.com,Jason1_Pan@pegatroncorp.com,Terry_Tzeng@pegatroncorp.com,Jack2_Hsu@pegatroncorp.com,Franck_Lin@pegatroncorp.com,James8_Chen@pegatroncorp.com,Calvin_Yu@pegatroncorp.com,Smal_Lin@pegatroncorp.com,Frank1_Yen@pegatroncorp.com,Andy1_Hsu@pegatroncorp.com,Hongde_Liu@pegatroncorp.com,Allen2_Chang@pegatroncorp.com,PennyC_Chen@pegatroncorp.com,Gordon1_Yu@pegatroncorp.com,Liche_Wu@pegatroncorp.com,Denny_Yang@pegatroncorp.com,MingChung_Wu@pegatroncorp.com,Hikaru_Fukaya@pegatroncorp.com,Lisa_Hsu@pegatroncorp.com,Rasmus_Lai@pegatroncorp.com,Ryan6_Lin@pegatroncorp.com,Joann_Liu@pegatroncorp.com,Parker6_Chen@pegatroncorp.com,Allen_Lee@pegatroncorp.com,Mike_Yang@pegatroncorp.com,Jeff6_Lin@pegatroncorp.com,Qilin_Zhu@pegatroncorp.com,Parker_Chen@pegatroncorp.com"

# --- 功能函數：從 Worker 腳本中動態提取最新版號 ---
get_release_version() {
    grep "^builtdate=" "$SCRIPT_DIR/auto_release_build_nogms_A15_v2.bash" | cut -d'"' -f2
}

# --- 功能函數：從 Worker 腳本中動態提取分支名稱並清理輸出 ---
get_clean_branch() {
    local full_branch=$(grep "^branch=" "$SCRIPT_DIR/auto_release_build_nogms_A15_v2.bash" | cut -d'"' -f2)
    echo "${full_branch#release/}" # 移除 "release/" 前綴以對齊伺服器目錄
}

# --- 功能函數：發送專業級版本通知信 (China Release 版) ---
send_smoke_test_report () {
    local variant=$1
    local version=$2
    local status=$3
    local branch=$4
    local SKU="China"
    
    local status_tag="STABLE"
    [ "$status" == "FAILED" ] && status_tag="FAILURE"

    local variant_cap="User"
    [ "$variant" == "userdebug" ] && variant_cap="Userdebug"

    # [主旨] [STATUS] Project Activity: ID (SKU/Variant) - Smoke Test: RESULT
    local mail_title="[$status_tag][Thorpe_A15] Release: REL_$version ($SKU/$variant_cap) - Smoke Test: $status"
    
    # [路徑轉義修正] 針對 China SKU Release 的目錄結構：
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
    content+="Smoke Test Status: ${status}\n"
    content+="------------------------------------------------------------\n"
    content+="Note: This build is marked as ${status_tag} based on automated smoke test results.\n"
    content+="Environmental items (GPS/NFC/WiFi Association) are excluded from\n"
    content+="overall status due to site signal instability.\n"
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
        ssh $REMOTE_TEST_USER@$TEST_SERVER "cd $REMOTE_TEST_DIR && ./.venv/bin/python3 trigger_job.py --build $version --type $variant --source release --sku nogms --remote-path $remote_path"
        if [ $? -eq 0 ]; then
            send_smoke_test_report "$variant" "$version" "PASS" "$branch"
        else
            send_smoke_test_report "$variant" "$version" "FAILED" "$branch"
        fi
    ) &
}

# =================================================================
# MAIN FLOW
# =================================================================
VERSION_TAG=$(get_release_version)
BRANCH_TAG=$(get_clean_branch)
echo "[V2-INFO] Detected Target Version: REL_$VERSION_TAG (Branch: $BRANCH_TAG)"

# 1. 執行 China Release Userdebug 編譯
echo "[V2-INFO] Starting China Release Userdebug build..."
bash "$SCRIPT_DIR/auto_release_build_nogms_A15_v2.bash"
trigger_remote_test "userdebug" "$VERSION_TAG" "$BRANCH_TAG"

# 2. 執行 China Release User 編譯
echo "[V2-INFO] Starting China Release User build..."
bash "$SCRIPT_DIR/auto_release_userbuild_nogms_A15_v2.bash"
trigger_remote_test "user" "$VERSION_TAG" "$BRANCH_TAG"

echo "[V2-SUCCESS] China Release pipeline execution finished."
wait
echo "[V2-DONE] All China Release tasks completed."
