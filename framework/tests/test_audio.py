from framework.adb_helper import run_adb_cmd, check_service_running, adb_pull
from framework.ui_automator import UIHelper
from framework.report_generator import HTMLReportGenerator
import time
import logging

def run_tests(ui: UIHelper, reporter: HTMLReportGenerator, specs=None, selectors=None, excluded=None):
    if not excluded: excluded = []
    logging.info("Running Audio Tests...")
    
    if not specs: specs = {}
    if not selectors: selectors = {}
    
    audio_stream = specs.get("audio_stream", 3)
    entropy_threshold = specs.get("audio_entropy_threshold", 50)
    record_dirs = specs.get("audio_record_dirs", ["/sdcard/Music", "/sdcard/Recordings", "/sdcard/Download"])
    
    ui_common = selectors.get("common", {})
    recorder_specs = selectors.get("recorder", {})
    
    if "Audio Service Check" not in excluded:
        if check_service_running("audio"):
            reporter.add_result("Audio", "Audio Service Check", True, "AudioService is running")
        else:
            reporter.add_result("Audio", "Audio Service Check", False, "AudioService not found")
    else:
        reporter.add_result("Audio", "Audio Service Check", True, "Skipped by profile", status_override="SKIP")
        
    if "Media Volume Control" not in excluded:
        try:
            run_adb_cmd(f"media volume --stream {audio_stream} --set 5")
            time.sleep(1)
            code, out = run_adb_cmd(f'dumpsys audio | grep -i "\\- STREAM_MUSIC" -A 5')
            if "5" in out and code == 0:
                reporter.add_result("Audio", "Media Volume Control", True, "Successfully set and read media volume via dumpsys")
            else:
                reporter.add_result("Audio", "Media Volume Control", False, f"Failed to verify media volume")
        except Exception as e:
            reporter.add_result("Audio", "Media Volume Control", False, str(e))
    else:
        reporter.add_result("Audio", "Media Volume Control", True, "Skipped by profile", status_override="SKIP")
        
    if "Audio HAL Initialization" not in excluded:
        try:
            _, out = run_adb_cmd("dumpsys media.audio_flinger")
            if "Hardware HAL" in out or "primary" in out.lower():
                reporter.add_result("Audio", "Audio HAL Initialization", True, "Audio HAL is loaded")
            else:
                reporter.add_result("Audio", "Audio HAL Initialization", False, "Could not verify Audio HAL")
        except Exception as e:
            reporter.add_result("Audio", "Audio HAL Initialization", False, str(e))
    else:
        reporter.add_result("Audio", "Audio HAL Initialization", True, "Skipped by profile", status_override="SKIP")

    # 4. Microphone Recording Test
    if "Microphone Recording" not in excluded:
        try:
            from framework.adb_helper import keep_screen_on
            keep_screen_on(True)
            logging.info("Starting Microphone Recording test...")
            target_dir = record_dirs[0]
            for d in record_dirs:
                code, _ = run_adb_cmd(f"ls -d {d}")
                if code == 0:
                    target_dir = d
                    break

            recorder_pkgs = ["com.android.soundrecorder", "com.google.android.soundrecorder", "com.sec.android.app.voicenote"]
            for pkg in recorder_pkgs:
                run_adb_cmd(f"pm grant {pkg} android.permission.RECORD_AUDIO")
                run_adb_cmd(f"pm grant {pkg} android.permission.WRITE_EXTERNAL_STORAGE")
                run_adb_cmd(f"pm grant {pkg} android.permission.READ_EXTERNAL_STORAGE")

            run_adb_cmd("am start -a android.provider.MediaStore.RECORD_SOUND")
            time.sleep(3)
            
            allow_btns = ui_common.get("allow_texts", ["Allow", "WHILE USING THE APP", "允許", "使用時允許", "使用时允许", "仅限一次", "仅限这一次", "永远允许", "始终允许", "始终", "仅在使用该应用时允许", "仅本次使用时允许"])
            confirm_btns = ui_common.get("confirm_texts", ["OK", "Next", "AGREE", "確定", "下一步", "同意", "允许", "同意并继续", "确认", "确定"])
            combined_popups = list(set(allow_btns + confirm_btns))
            
            pattern = "|".join(f".*{btn}.*" for btn in combined_popups)
            popup_wait_end = time.time() + 10
            while time.time() < popup_wait_end:
                try:
                    # DEBUG LOGGING
                    logging.info(f"DEBUG UIAutomator2: Current package is {ui.d.info.get('currentPackageName')}")
                    xml_dump = ui.d.dump_hierarchy()
                    logging.info(f"DEBUG UIAutomator2: XML dump size {len(xml_dump)} bytes. '允许' in XML: {'允许' in xml_dump}")

                    btn = ui.d(textMatches=f"(?i)({pattern})", clickable=True)
                    if btn.exists(timeout=1):
                        logging.info(f"Clicking audio popup: {btn.info.get('text', 'unknown')}")
                        btn.click(timeout=1)
                        time.sleep(1.5)
                        popup_wait_end = time.time() + 5
                except Exception as e:
                    logging.warning(f"Error in audio dialog bypass: {e}")

            def find_start_btn():
                specific_id = recorder_specs.get("shutter_id")
                if specific_id:
                    btn = ui.d(resourceId=specific_id)
                    if btn.exists(timeout=2): return btn
                for res_id in [".*record_button.*", ".*start_button.*", ".*btn_record.*", ".*shutter.*"]:
                    btn = ui.d(resourceIdMatches=res_id)
                    if btn.exists(timeout=1): return btn
                return None

            start_button = find_start_btn()
            
            if not start_button:
                logging.info("Start button not found. Blindly pressing back to clear potential file list or dialog...")
                ui.d.press("back")
                time.sleep(2)
                start_button = find_start_btn()
            
            if start_button:
                start_button.click()
                time.sleep(8) # Record
                
                stop_clicked = False
                stop_id = recorder_specs.get("stop_id")
                if stop_id:
                    btn = ui.d(resourceId=stop_id)
                    if btn.exists(timeout=2):
                        btn.click()
                        stop_clicked = True
                
                if not stop_clicked:
                    for res_id in [".*stop_button.*", ".*done_button.*", ".*save_button.*"]:
                        btn = ui.d(resourceIdMatches=res_id)
                        if btn.exists(timeout=1):
                            btn.click()
                            stop_clicked = True
                            break
                
                time.sleep(1)
                for dialog_btn in ["Save", "OK", "儲存", "確定", "保存"]:
                    btn = ui.d(textMatches=f"(?i){dialog_btn}")
                    if btn.exists(timeout=1):
                        btn.click()
                        time.sleep(1)

                time.sleep(3)
                find_cmd = f"find {target_dir} -maxdepth 2 -mmin -2 -type f | grep -E 'amr|m4a|3gp|wav'"
                _, find_out = run_adb_cmd(find_cmd)
                
                if find_out.strip():
                    latest_file = find_out.strip().split('\n')[-1]
                    host_tmp_path = f"/tmp/audio_verify_{int(time.time())}.amr"
                    if adb_pull(latest_file, host_tmp_path):
                        try:
                            with open(host_tmp_path, "rb") as f:
                                data = f.read(2000)
                                e_score = len(set(data))
                            if e_score > entropy_threshold:
                                reporter.add_result("Audio", "Microphone Hardware Verification", True, f"PASS (Score: {e_score})")
                            else:
                                reporter.add_result("Audio", "Microphone Hardware Verification", False, f"FAIL (Score: {e_score})")
                        except Exception as e:
                            reporter.add_result("Audio", "Microphone Hardware Verification", False, f"Analysis Error: {e}")
                    else:
                        reporter.add_result("Audio", "Microphone Hardware Verification", False, "Failed to pull audio file from device")
                else:
                    reporter.add_result("Audio", "Microphone Recording", False, "No new audio file found")
            else:
                reporter.add_result("Audio", "Microphone Recording", False, "Could not find Record button")
            
            ui.go_home()
        except Exception as e:
            reporter.add_result("Audio", "Microphone Recording", False, str(e))
    else:
        reporter.add_result("Audio", "Microphone Recording", True, "Skipped by profile", status_override="SKIP")
