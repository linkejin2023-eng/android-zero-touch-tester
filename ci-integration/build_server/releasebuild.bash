upload_jsonfile () {
    password=32600
    expect -c "
        set timeout 2400
        spawn scp -r /home/server/bin/build_info.json nick_chuang@10.192.188.16:/media/share/thorpe/Android_15/Release_pega/REL_02.02.02.260411
        expect \"password:\"
        send \"${password}\r\"
        expect eof"
}

#main
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATE=`date +%Y%m%d`
VERSION="02.02.02.260411"
VARIANT="userdebug"
sed "s/02.02.01.260331/$VERSION/g" "$SCRIPT_DIR/auto_release_build_A15.bash" > "$SCRIPT_DIR/auto_release_build_A15_tmp.bash"
sed 's/2.2.1/2.2.2/' "$SCRIPT_DIR/auto_release_build_A15_tmp.bash" > "$SCRIPT_DIR/auto_release_build_A15_tmp1.bash"
mv "$SCRIPT_DIR/auto_release_build_A15_tmp1.bash" "$SCRIPT_DIR/auto_release_build_A15.bash"
rm -rf "$SCRIPT_DIR/auto_release_build_A15_tmp.bash"

sed "s/02.02.01.260331/$VERSION/g" "$SCRIPT_DIR/auto_release_userbuild_A15.bash" > "$SCRIPT_DIR/auto_release_userbuild_A15_tmp.bash"
sed 's/2.2.1/2.2.2/' "$SCRIPT_DIR/auto_release_userbuild_A15_tmp.bash" > "$SCRIPT_DIR/auto_release_userbuild_A15_tmp1.bash"
mv "$SCRIPT_DIR/auto_release_userbuild_A15_tmp1.bash" "$SCRIPT_DIR/auto_release_userbuild_A15.bash"
rm -rf "$SCRIPT_DIR/auto_release_userbuild_A15_tmp.bash"

rm -rf "$SCRIPT_DIR/A15_artifact/artifact/";bash "$SCRIPT_DIR/auto_release_build_A15.bash";mv /home/server/thorpe_dailybuild_A15/shell-script/artifact "$SCRIPT_DIR/A15_artifact/"

VARIANT=user
bash "$SCRIPT_DIR/auto_release_userbuild_A15.bash"

cd /home/server/bin/
sed 's/02.02.01.260331/02.02.02.260411/' build_info.json > build_info_tmp.json
sed 's/2026-03-31/2026-04-11' build_info_tmp.json > build_info_tmp.json
mv build_info_tmp.json build_info.json

upload_jsonfile
