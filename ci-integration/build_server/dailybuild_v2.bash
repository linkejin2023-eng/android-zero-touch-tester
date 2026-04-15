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

# --- 功能函數：觸發遠端自動化測試 ---
trigger_remote_test () {
    local variant=$1
    local built_date=$2
    local result_file="$SCRIPT_DIR/test_result_${variant}.tmp"
    
    echo "[V2-INFO] Triggering automated test on $TEST_SERVER for daily $variant ($built_date)..."
    
    # Daily 路徑規格
    local zipfile="${built_date}_thorpe_dev_${variant}_a15_gms"
    local remote_path="${REMOTE_DAILY_ROOT}/${zipfile}/fastboot.zip"
    
    local extra_flags=""
    if [ "$DRY_RUN" = true ]; then
        extra_flags="--check-only"
    fi

    # 異步執行並記錄結果至臨時檔
    (
        ssh $REMOTE_TEST_USER@$TEST_SERVER "cd $REMOTE_TEST_DIR && ./.venv/bin/python3 trigger_job.py --build $built_date --type $variant --source daily $extra_flags --remote-path $remote_path"
        if [ $? -eq 0 ]; then
            echo "SUCCESS" > "$result_file"
        else
            echo "FAILED" > "$result_file"
        fi
    ) &
}

send_integrated_report () {
    local date_debug=$1
    local date_user=$2
    
    local status_debug="PENDING"
    local status_user="PENDING"
    [ -f "$SCRIPT_DIR/test_result_userdebug.tmp" ] && status_debug=$(cat "$SCRIPT_DIR/test_result_userdebug.tmp")
    [ -f "$SCRIPT_DIR/test_result_user.tmp" ] && status_user=$(cat "$SCRIPT_DIR/test_result_user.tmp")
    
    local mail_title="[Thorpe_A15][Daily_Report][${date_user}] Summary"
    local content="Daily Build & Sanity Test Integrated Report\n"
    content+="==========================================\n"
    content+="Build Date: ${date_user}\n\n"
    content+="1. Userdebug Build: DONE\n"
    content+="   Test Status: ${status_debug}\n\n"
    content+="2. User Build: DONE\n"
    content+="   Test Status: ${status_user}\n\n"
    content+="Report Path: \\\\10.192.188.16\\share\\thorpe\\Android_15\\dailybuild\\\n"
    content+="==========================================\n"
    
    echo -e "$content" | mutt -s "$mail_title" -- "$MEMBERS"
    echo "[V2-INFO] Integrated report sent to members."
    
    # 清理臨時檔
    rm -f "$SCRIPT_DIR/test_result_*.tmp"
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

# 5. 發送整合報表
send_integrated_report "$DATE_DEBUG" "$DATE_USER"
