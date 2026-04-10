#!/bin/bash
# =================================================================
# releasebuild_v2.bash - CI/CD 自動化整合版 (Non-Invasive)
# =================================================================

# [測試開關] 若想跳過 4-5 小時編譯，請設為 true 進行流程測試
DRY_RUN=false

# [維護重點] 每個新版本 Build 時，請僅修改這兩行：
VERSION="02.02.02.260411"
VERSION_DATE="2026-04-11"

# [註] 除非原始範本 (.bash 檔) 內的版本號被 SCM 手動更改了，否則以下兩行不需變動
OLD_VERSION="02.02.01.260331"
OLD_DATE="2026-03-31"

TEST_SERVER="10.192.220.17"
IMAGE_SERVER="10.192.188.16"
REMOTE_USER="nick_chuang"
PASSWORD="32600"

# --- 功能函數：同步上傳 Build Info ---
upload_json_to_server () {
    local variant=$1
    echo "[V2-INFO] Syncing build_info.json for $variant..."
    
    pushd /home/server/bin/ > /dev/null
    sed "s/$OLD_VERSION/$VERSION/g" build_info.json > build_info_tmp.json
    sed -i "s/$OLD_DATE/$VERSION_DATE/g" build_info_tmp.json
    
    # 執行上傳
    expect -c "
        set timeout 300
        spawn scp build_info_tmp.json $REMOTE_USER@$IMAGE_SERVER:/media/share/thorpe/Android_15/Release_pega/REL_$VERSION/$variant/build_info.json
        expect \"password:\"
        send \"${PASSWORD}\r\"
        expect eof"
    
    popd > /dev/null
}

# --- 功能函數：觸發遠端自動化測試 ---
trigger_remote_test () {
    local variant=$1
    echo "[V2-INFO] Triggering automated test on $TEST_SERVER for $variant..."
    
    local extra_flags=""
    if [ "$DRY_RUN" = true ]; then
        extra_flags="--check-only"
    fi

    (ssh franck_lin@$TEST_SERVER "cd /home/franck_lin/auto_test/ && ./.venv/bin/python3 trigger_job.py --build $VERSION --type $variant --source release $extra_flags" || echo "[V2-WARN] Remote trigger for $variant failed, but continuing build pipeline...") &
}

# =================================================================
# MAIN FLOW - 正式編譯流程
# =================================================================

# 1. 準備編譯腳本 (永遠讀取原始 .bash 檔案)
sed "s/$OLD_VERSION/$VERSION/g" auto_release_build_A15.bash > auto_release_build_A15_v2.bash
sed -i "s/2.2.1/2.2.2/g" auto_release_build_A15_v2.bash

sed "s/$OLD_VERSION/$VERSION/g" auto_release_userbuild_A15.bash > auto_release_userbuild_A15_v2.bash
sed -i "s/2.2.1/2.2.2/g" auto_release_userbuild_A15_v2.bash

# 2. 執行 Userdebug 編譯
if [ "$DRY_RUN" = true ]; then
    echo "[V2-DRYRUN] Skipping Userdebug build (Simulated)..."
    sleep 2
else
    echo "[V1-ORIGIN] Starting Userdebug build..."
    rm -rf A15_artifact/artifact/
    bash auto_release_build_A15_v2.bash
    mv /home/server/thorpe_dailybuild_A15/shell-script/artifact A15_artifact/
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
    bash auto_release_userbuild_A15_v2.bash
fi

# 5. [V2 插入] User 完工 -> 上傳 JSON -> 觸發測試
upload_json_to_server "user"
trigger_remote_test "user"

echo "[V2-SUCCESS] Pipeline execution finished (DRY_RUN=$DRY_RUN)."
wait # 等待背景任務結束以確保游標正常歸還
