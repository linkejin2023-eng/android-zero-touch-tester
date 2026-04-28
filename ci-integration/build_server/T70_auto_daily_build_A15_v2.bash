#!/bin/bash
export USER=$(whoami)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_ARTIFACT_DIR="/home/server/bin/A15_artifact"

# [MODIFIED] 支援從 Orchestrator 傳入固定 ID，確保 Build/Test 同步
builtdate=${3:-$(date +%Y%m%d%H%M)}

# 將本次編譯的時間戳記寫入臨時檔 (供主控腳本回讀，雖然 Orchestrator 已經知道了)
echo "$builtdate" > "$SCRIPT_DIR/last_builtdate_${2}.tmp"

members="Nick_Chuang@pegatroncorp.com,Billy_Chen@pegatroncorp.com,Franck_Lin@pegatroncorp.com"
success_content="Done building targets. \(Image path: \\\\\\\10.192.188.16\\\\\\share\\\\\\thorpe\)"
fail_content="Building failed with error."
LOGFILE=${directory}/shell-script/buildlog.zip

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

sync_code () {
    cd ${directory}/.repo/manifests; git reset --hard; git clean -fd; git pull 2>&1 | tee pull.log; cd -
    cd ${directory};repo forall -c 'pwd;git pull pandora $BRANCH:$BRANCH' 2>&1 | tee pull.log; cd -
	cd ${directory}/QCM6490_apps_qssi15/LINUX/android/.repo/manifests;git reset --hard; git clean -fd; git pull 2>&1 | tee pull.log; cd -
	cd ${directory}/QCM6490_apps_qssi15/LINUX/android;repo forall -c 'pwd;git pull pandora ${BRANCH}:${BRANCH}' 2>&1 | tee pull.log; cd -
}

clean_code () {
    cd ${directory}/shell-script
    bash build_all_A15.bash clean_all; chk_error $? "Execute build_all.sh failed"
}

build_code () {
	cd ${directory}/shell-script
    bash build_all_A15.bash thorpe $BUILD_VARIANT -gs 2>&1 | tee buildlog.txt; chk_error $? "Execute build_all.sh failed"
    cp -r ${directory}/shell-script/buildlog.txt /home/server/bin
}

copy_image () {
    mkdir -p ${directory}/shell-script/artifact/${zipfile}
	cd ${directory}/QCM6490_apps_qssi15/LINUX/android;repo manifest -o manifest_${builtdate}_qssi15.xml -r;mv manifest_${builtdate}_qssi15.xml ${directory}/shell-script/artifact/${zipfile}
    cd ${directory}/shell-script; repo manifest -o manifest_${builtdate}.xml -r; mv manifest_${builtdate}.xml artifact/${zipfile}
    cp -r ${directory}/shell-script/artifact/symbol_backup.zip ${directory}/shell-script/artifact/${zipfile}/
	cp -r ${directory}/shell-script/buildlog.txt artifact/
	zip -r buildlog.zip buildlog.txt
	cp -r ${directory}/shell-script/ota_package_a15 artifact/
	cd artifact
    zip -r qfil.zip qfil
    zip -r fastboot.zip fastboot
    mv *.zip ${zipfile}
}

upload_image () {
    password=32600
    expect -c "
        set timeout 2400
        spawn scp -r ${directory}/shell-script/artifact/${zipfile} nick_chuang@10.192.188.16:/media/share/thorpe/Android_15/dailybuild/
        expect \"password:\"
        send \"${password}\r\"
        expect eof"
}

#main
export BRANCH="$1";
export BUILD_VARIANT="$2";
case $BRANCH in
"thorpe_dev" ) directory="/home/server/thorpe_dailybuild_A15" ;;
"T70-A15-2.1.0-CN" ) directory="/mnt/data_1/server/thorpe_A15_dailybuild" ;;
"thorpe_dev_test_260407" ) directory="/mnt/data_1/server/thorpe_A15_testbuild" ;;
*) echo "The $BRANCH is not support"; exit 1 ;;
esac

zipfile=${builtdate}_${BRANCH}_${BUILD_VARIANT}_a15_gms
image_name=${builtdate}_${BRANCH}_${BUILD_VARIANT}_a15_gms

clean_code

# [MODIFIED] 實驗分支跳過同步，保留本地修改
if [ "$BRANCH" == "thorpe_dev_test_260407" ]; then
    echo "[INFO] Experimental branch $BRANCH detected. Skipping sync_code..."
else
    sync_code
fi

build_code
copy_image
upload_image

mv ${directory}/shell-script/artifact/${zipfile} ${LOCAL_ARTIFACT_DIR}/
exit 0
