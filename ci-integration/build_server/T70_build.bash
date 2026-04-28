## main ##
export BRANCH="$1";
export VARIANT="$2";
REMOTE_USER="server"     # Image Server User
PASSWORD="pega#1234"
IMAGE_SERVER="10.192.188.16"
BUILD_SERVER_A="10.192.188.8"
BUILD_SERVER_B="10.192.188.25"
SCRIPT_DIR="/home/server/bin"
LOCAL_ARTIFACT_DIR="/home/server/bin/A15_artifact"
SUB_SCRIPT="T70_auto_daily_build_A15.bash"

case $BRANCH in
"thorpe_dev" )
ssh $REMOTE_USER@$BUILD_SERVER_A "cd $SCRIPT_DIR && rm -rf $LOCAL_ARTIFACT_DIR/artifact/ && bash $SCRIPT_DIR/$SUB_SCRIPT $BRANCH userdebug && bash $SCRIPT_DIR/$SUB_SCRIPT $BRANCH user"
;;
"T70-A15-2.1.0-CN" )
	case $VARIANT in
	"all" )
	ssh $REMOTE_USER@$BUILD_SERVER_B "cd $SCRIPT_DIR && rm -rf $LOCAL_ARTIFACT_DIR/artifact/ && bash $SCRIPT_DIR/$SUB_SCRIPT $BRANCH userdebug && bash $SCRIPT_DIR/$SUB_SCRIPT $BRANCH user"
	;;
	*)
	ssh $REMOTE_USER@$BUILD_SERVER_B "cd $SCRIPT_DIR && rm -rf $LOCAL_ARTIFACT_DIR/artifact/ && bash $SCRIPT_DIR/$SUB_SCRIPT $BRANCH $VARIANT"
	esac
;;
"thorpe_dev_test_260407" )
	case $VARIANT in
	"all" )
	ssh $REMOTE_USER@$BUILD_SERVER_B "cd $SCRIPT_DIR && rm -rf $LOCAL_ARTIFACT_DIR/artifact/ && bash $SCRIPT_DIR/$SUB_SCRIPT $BRANCH userdebug && bash $SCRIPT_DIR/$SUB_SCRIPT $BRANCH user"
	;;
	*)
	ssh $REMOTE_USER@$BUILD_SERVER_B "cd $SCRIPT_DIR && rm -rf $LOCAL_ARTIFACT_DIR/artifact/ && bash $SCRIPT_DIR/$SUB_SCRIPT $BRANCH $VARIANT"
	esac
;;
*)
 echo "The $BRANCH is not support"
esac
