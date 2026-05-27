#!/bin/bash
# =================================================================
# unified_build_A15.bash - 統一編譯與上傳腳本 (Unified Architecture)
# =================================================================

# 接收參數 (由 Orchestrator 動態傳入)
export BRANCH="$1"
export BUILD_VARIANT="$2"
export BUILD_ID="$3"       # Daily: 202605271030, Release: 02.02.01.260527
export SKU="$4"            # gms or china
export SOURCE="$5"         # daily or release
export WORKSPACE="$6"      # 本地 codebase 路徑 (由 Orchestrator 查表給予)

if [ "$#" -lt 6 ]; then
    echo "[ERROR] Invalid usage. Expected 6 arguments."
    echo "Usage: bash unified_build_A15.bash <BRANCH> <VARIANT> <BUILD_ID> <SKU> <SOURCE> <WORKSPACE>"
    exit 1
fi

echo "=========================================================="
echo " Starting Unified Build: $SKU | $SOURCE | $BUILD_VARIANT"
echo " ID: $BUILD_ID | Branch: $BRANCH"
echo " Workspace: $WORKSPACE"
echo "=========================================================="

# 檢查路徑合法性
if [ ! -d "$WORKSPACE" ]; then
    echo "[ERROR] Workspace directory $WORKSPACE does not exist!"
    exit 1
fi

export USER=$(whoami)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_ARTIFACT_DIR="/home/server/bin/A15_artifact"

# [MODIFIED] 實驗分支跳過同步，保留本地修改 (繼承舊邏輯)
sync_code () {
    if [ "$BRANCH" == "thorpe_dev_test_260407" ]; then
        echo "[INFO] Experimental branch $BRANCH detected. Skipping sync_code..."
        return
    fi
    cd ${WORKSPACE}/.repo/manifests; git reset --hard; git clean -fd; git pull 2>&1 | tee pull.log; cd -
    cd ${WORKSPACE}; repo forall -c "pwd;git pull pandora $BRANCH:$BRANCH" 2>&1 | tee pull.log; cd -
    cd ${WORKSPACE}/QCM6490_apps_qssi15/LINUX/android/.repo/manifests; git reset --hard; git clean -fd; git pull 2>&1 | tee pull.log; cd -
    cd ${WORKSPACE}/QCM6490_apps_qssi15/LINUX/android; repo forall -c "pwd;git pull pandora ${BRANCH}:${BRANCH}" 2>&1 | tee pull.log; cd -
}

chk_error () {
    if [ "$1" -eq 0 ]; then
        case $2 in
            "[A15] Failed to"*) echo "ERROR: $2"; exit 1 ;;
        esac
    fi
    if [ "$1" -ne 0 ]; then
        case $2 in 
            "Execute build_all_A15.bash failed") echo "ERROR: $2"; exit 1 ;;
        esac
    fi
}

clean_code () {
    cd ${WORKSPACE}/shell-script
    bash build_all_A15.bash clean_all; chk_error $? "Execute build_all.sh failed"
}

build_code () {
    cd ${WORKSPACE}/shell-script
    # 動態產生編譯參數
    local build_flags="thorpe $BUILD_VARIANT"
    if [ "$SKU" == "gms" ]; then
        build_flags+=" -gs"
    fi
    
    echo "[INFO] Executing: bash build_all_A15.bash $build_flags"
    bash build_all_A15.bash $build_flags 2>&1 | tee buildlog.txt; chk_error $? "Execute build_all.sh failed"
    cp -r ${WORKSPACE}/shell-script/buildlog.txt /home/server/bin
}

copy_image () {
    zipfile="${BUILD_ID}_${BRANCH}_${BUILD_VARIANT}_a15_${SKU}"
    echo "[INFO] Packaging artifacts to $zipfile..."
    
    mkdir -p ${WORKSPACE}/shell-script/artifact/${zipfile}
    
    # 產出 XML Manifest
    cd ${WORKSPACE}/QCM6490_apps_qssi15/LINUX/android; repo manifest -o manifest_${BUILD_ID}_qssi15.xml -r; mv manifest_${BUILD_ID}_qssi15.xml ${WORKSPACE}/shell-script/artifact/${zipfile}
    cd ${WORKSPACE}/shell-script; repo manifest -o manifest_${BUILD_ID}.xml -r; mv manifest_${BUILD_ID}.xml artifact/${zipfile}
    
    # 複製 Log 與 Symbol 備份
    cp -r ${WORKSPACE}/shell-script/artifact/symbol_backup.zip ${WORKSPACE}/shell-script/artifact/${zipfile}/
    cp -r ${WORKSPACE}/shell-script/buildlog.txt artifact/
    cd artifact
    zip -r buildlog.zip buildlog.txt
    
    # 【RELEASE 專屬邏輯】: 額外攜帶 OTA 包
    if [ "$SOURCE" == "release" ]; then
        echo "[INFO] Release Source detected. Packaging OTA bundles..."
        cp -r ${WORKSPACE}/shell-script/ota_package_a15/thorpe-ota.zip ${WORKSPACE}/shell-script/artifact/${zipfile}/thorpe-${BUILD_ID}-ota.zip
        cp -r ${WORKSPACE}/shell-script/ota_package_a15/thorpe-target.zip ${WORKSPACE}/shell-script/artifact/${zipfile}/
        cp -r ${WORKSPACE}/shell-script/ota_package_a15/thorpe-factory_reset-ota.zip ${WORKSPACE}/shell-script/artifact/${zipfile}/thorpe-${BUILD_ID}_wipe-ota.zip
    else
        # Daily 保持舊有邏輯，僅帶上 ota_package_a15 整個資料夾供參考
        cp -r ${WORKSPACE}/shell-script/ota_package_a15 .
    fi
    
    zip -r qfil.zip qfil
    zip -r fastboot.zip fastboot
    mv *.zip ${zipfile}
}

upload_image () {
    echo "[INFO] Uploading artifacts via SCP..."
    
    # 動態決定上傳路徑
    if [ "$SOURCE" == "release" ]; then
        upload_dest="/media/share/thorpe/Android_15/Release_pega/REL_${BUILD_ID}/${BUILD_VARIANT}"
    else
        upload_dest="/media/share/thorpe/Android_15/dailybuild"
    fi
    
    local image_server="nick_chuang@10.192.188.16"
    local password="32600"
    
    # 先遠端建立資料夾確保路徑存在
    echo "[INFO] Creating remote path: $upload_dest"
    expect -c "
        set timeout 30
        spawn ssh ${image_server} \"mkdir -p ${upload_dest}\"
        expect \"password:\"
        send \"${password}\r\"
        expect eof"

    # 上傳產出物
    expect -c "
        set timeout 2400
        spawn scp -r ${WORKSPACE}/shell-script/artifact/${zipfile} ${image_server}:${upload_dest}/
        expect \"password:\"
        send \"${password}\r\"
        expect eof"
}

# --- 執行主流程 ---
clean_code
sync_code
build_code
copy_image
upload_image

mkdir -p ${LOCAL_ARTIFACT_DIR}
mv ${WORKSPACE}/shell-script/artifact/${zipfile} ${LOCAL_ARTIFACT_DIR}/
echo "[SUCCESS] Build & Upload Complete!"
exit 0
