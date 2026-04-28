#!/bin/bash
# =================================================================
# T70_build_v2.bash - 主控入口腳本 (支援 Orchestrator ID 同步)
# =================================================================

export BRANCH="$1";
export VARIANT="$2";
export TIMESTAMP="$3"; # 接收從 orchestrator 傳入的固定 ID

REMOTE_USER="server"
BUILD_SERVER_A="10.192.188.8"
BUILD_SERVER_B="10.192.188.25"
SCRIPT_DIR="/home/server/bin"
LOCAL_ARTIFACT_DIR="/home/server/bin/A15_artifact"
SUB_SCRIPT="T70_auto_daily_build_A15_v2.bash"

# 防呆：如果沒有傳入 TIMESTAMP，由本腳本生成一個，確保後續一致
if [ -z "$TIMESTAMP" ]; then
    TIMESTAMP=$(date +%Y%m%d%H%M)
    echo "[INFO] No timestamp provided, generated: $TIMESTAMP"
fi

case $BRANCH in
"thorpe_dev" )
    # 在 v2 中，我們讓 orchestrator 決定跑哪個 variant，所以這裡不再 hardcode 跑兩次
    ssh $REMOTE_USER@$BUILD_SERVER_A "cd $SCRIPT_DIR && rm -rf $LOCAL_ARTIFACT_DIR/artifact/ && bash $SCRIPT_DIR/$SUB_SCRIPT $BRANCH $VARIANT $TIMESTAMP"
;;
"T70-A15-2.1.0-CN" | "thorpe_dev_test_260407" )
    ssh $REMOTE_USER@$BUILD_SERVER_B "cd $SCRIPT_DIR && rm -rf $LOCAL_ARTIFACT_DIR/artifact/ && bash $SCRIPT_DIR/$SUB_SCRIPT $BRANCH $VARIANT $TIMESTAMP"
;;
*)
 echo "The $BRANCH is not support"
 exit 1
esac
