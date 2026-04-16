export USER=$(whoami)
directory="/mnt/data_1/server/thorpe_A15_dailybuild"
branch="release/T70-A15-2.1.0-CN"
#branch="thorpe_dev_lcd_rotate"
builtdate="02.01.06.N.260310"
manifest_name="T70-A15-2.1.5-CN-RC6"
members="Billy_Chen@pegatroncorp.com,Aaren_Bai@pegatroncorp.com,Nick_Chuang@pegatroncorp.com,Jason1_Pan@pegatroncorp.com,Terry_Tzeng@pegatroncorp.com,Jack2_Hsu@pegatroncorp.com,Franck_Lin@pegatroncorp.com,James8_Chen@pegatroncorp.com,Calvin_Yu@pegatroncorp.com,Smal_Lin@pegatroncorp.com,Frank1_Yen@pegatroncorp.com,Andy1_Hsu@pegatroncorp.com,Hongde_Liu@pegatroncorp.com,Allen2_Chang@pegatroncorp.com,PennyC_Chen@pegatroncorp.com,Gordon1_Yu@pegatroncorp.com,Liche_Wu@pegatroncorp.com,Denny_Yang@pegatroncorp.com,MingChung_Wu@pegatroncorp.com,Lisa_Hsu@pegatroncorp.com,Rasmus_Lai@pegatroncorp.com,Ryan6_Lin@pegatroncorp.com,Joann_Liu@pegatroncorp.com,Parker6_Chen@pegatroncorp.com,Allen_Lee@pegatroncorp.com,Mike_Yang@pegatroncorp.com,Jeff6_Lin@pegatroncorp.com,Qilin_Zhu@pegatroncorp.com,Parker_Chen@pegatroncorp.com"
#members="Nick_Chuang@pegatroncorp.com"
success_content="Done building targets. \(Image path: \\\\\\\10.192.188.16\\\\\\share\\\\\\thorpe\)"
fail_content="Building failed with error."

chk_error () {
    if [ "$1" -eq 0 ]
    then
        case $2 in
            "[A15] Failed to"*)
                echo "ERROR: $2"
                #echo $2 | mutt -s $mail_title -- $members
                exit 1
            ;;
        esac
    fi
    if [ "$1" -ne 0 ]
    then
        case $2 in 
            "Execute build_all_A15.bash failed")
                echo "ERROR: $2"
                #echo $fail_content | mutt -s $mail_title -- $members
                exit
            ;;
        esac
    fi
}

sync_code () {
    cd ${directory}/.repo/manifests; git reset --hard; git clean -fd; git pull 2>&1 | tee pull.log; cd -
    #cd ${directory}/buildscripts; git reset --hard; git clean -fd;
    cd ${directory};repo forall -c 'pwd;git pull pandora release/T70-A15-2.1.0-CN:release/T70-A15-2.1.0-CN' 2>&1 | tee pull.log; cd -
	cd ${directory}/QCM6490_apps_qssi15/LINUX/android/.repo/manifests;git reset --hard; git clean -fd; git pull 2>&1 | tee pull.log; cd -
	cd ${directory}/QCM6490_apps_qssi15/LINUX/android;repo forall -c 'pwd;git pull pandora release/T70-A15-2.1.0-CN:release/T70-A15-2.1.0-CN' 2>&1 | tee pull.log; cd -
}

clean_code () {
    cd ${directory}/shell-script
    bash build_all_A15.bash clean_all; chk_error $? "Execute build_all.sh failed"
}

build_code () {
    cp -r /home/server/bin/relase_script/build_A15.bash ${directory}/shell-script
	cd ${directory}/shell-script
    bash build_all_A15.bash thorpe $version -s 2>&1 | tee buildlog_user.txt; chk_error $? "Execute build_all.sh failed"
#     bash build_all_A15.bash thorpe $version; chk_error $? "Execute build_all.sh failed"
    cp -r ${directory}/shell-script/buildlog_user.txt /home/server/bin
}

copy_image () {
    mkdir -p ${directory}/shell-script/artifact/${zipfile}
	cd ${directory}/QCM6490_apps_qssi15/LINUX/android;repo manifest -o ${manifest_name}_qssi15.xml -r;mv ${manifest_name}_qssi15.xml ${directory}/shell-script/artifact/${zipfile}
    cd ${directory}/shell-script; repo manifest -o ${manifest_name}.xml -r; mv ${manifest_name}.xml artifact/${zipfile}
    cp -r ${directory}/shell-script/artifact/symbol_backup.zip ${directory}/shell-script/artifact/${zipfile}/
	cp -r ${directory}/shell-script/buildlog_user.txt artifact/
	cp -r ${directory}/shell-script/ota_package_a15/thorpe-ota.zip ${directory}/shell-script/artifact/${zipfile}/thorpe-${builtdate}-ota.zip
	cp -r ${directory}/shell-script/ota_package_a15/thorpe-target.zip ${directory}/shell-script/artifact/${zipfile}/
	cp -r ${directory}/shell-script/ota_package_a15/thorpe-factory_reset-ota.zip ${directory}/shell-script/artifact/${zipfile}/thorpe-${builtdate}_wipe-ota.zip
	cd artifact
    #zip -r debug.zip debug
    zip -r qfil.zip qfil
    zip -r fastboot.zip fastboot
# mkdir -p ${zipfile}
    mv *.zip ${zipfile}
    #mv ota ${zipfile}
}

copy_symbol () {
    cd ${directory}/shell-script/artifact;mkdir symbol_backup;cd symbol_backup
    cp -r ${directory}/LINUX/android/out/target/product/lahaina/obj/KERNEL_OBJ/vmlinux ./
	cp -r ${directory}/aop_proc/core/bsp/aop/build/kodiak/AOP_AAAAANAZO.elf ./
    cp -r ${directory}/boot_images/Build/KodiakLAA/Loader/RELEASE_CLANG100LINUX/AARCH64/QcomPkg/XBLLoader/XBLLoader/DEBUG/XBLLoader.dll ./
	cp -r ${directory}/trustzone_images/ssg/bsp/qsee/build/IAGAANAA/qsee.elf ./
	cp -r ${directory}/trustzone_images/ssg/bsp/devcfg/build/IAGAANAA/devcfg.elf ./
	cp -r ${directory}/trustzone_images/ssg/bsp/monitor/build/IAGAANAA/mon.elf ./
	cp -r ${directory}/trustzone_images/core/bsp/hypervisor/build/IAGAANAA/hyp.elf ./
	cp -r ${directory}/shell-script/artifact/symbol_backup ${directory}/shell-script/artifact/${zipfile}/
}



upload_image () {
    password=32600
    expect -c "
        set timeout 2400
        spawn scp -r ${directory}/shell-script/artifact/${zipfile} nick_chuang@10.192.188.16:/media/share/thorpe/Android_15/Release_pega/REL_02.01.06.N.260310/
        expect \"password:\"
        send \"${password}\r\"
        expect eof"
    #echo $success_content | mutt -s $mail_title -- $members
}

auto_tag () {
    cd ${directory}; dailytag=T70-A15-2.1.6-CN-FORK
#    cd .repo/manifests; git tag $dailytag; git push origin $dailytag 2>&1 | tee tag.log; grep -iE 'error:|fatal|rejected' tag.log; chk_error $? "[A15] Failed to push tag to Pega Gitlab"
#    cd ${directory}; repo forall -c "git tag $dailytag"; repo forall -c "git push pandora $dailytag" 2>&1 | tee tag.log; grep -iE 'error:|fatal|rejected' tag.log; chk_error $? "[A15] Failed to push tag to Pega Gitlab"
    cd ${directory}/QCM6490_apps_qssi15/LINUX/android/;repo forall -c "git tag $dailytag";repo forall -c "git push pandora $dailytag" 2>&1 | tee tag.log
	cd ${directory};repo forall -c "git tag $dailytag";repo forall -c "git push pandora $dailytag" 2>&1 | tee tag.log
}

#main
version="user"
zipfile=${builtdate}_${branch}_${version}_a15_nogms
#zipfile=${builtdate}_${branch}_${version}_a15
#mail_title=[Thorpe_A15][daily_build_${builtdate}][$branch][$version]
clean_code
#sync_code
build_code
copy_image
#copy_symbol
upload_image

# [V2-CLEANUP] Old notification moved to china_releasebuild_v2.bash
# success_content='Done building targets. \\\10.192.188.16\share\\thorpe\Android_15\Release_pega\REL_02.01.06.N.260310 \n '
# mail_title=[Thorpe_A15][release_build_REL_${builtdate}][$branch][NOGMS]
# echo -e $success_content | mutt -s $mail_title -- $members

#auto_tag
