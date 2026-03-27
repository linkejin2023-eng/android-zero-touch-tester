from framework.adb_helper import run_adb_cmd, check_service_running
from framework.ui_automator import UIHelper
from framework.report_generator import HTMLReportGenerator
import time
import logging

def run_tests(ui: UIHelper, reporter: HTMLReportGenerator):
    logging.info("Running Audio Tests...")
    
    # 1. Check Audio Service
    if check_service_running("audio"):
        reporter.add_result("Audio", "Audio Service Check", True, "AudioService is running")
    else:
        reporter.add_result("Audio", "Audio Service Check", False, "AudioService not found")
        
    # 2. Adjust Volume via ADB
    try:
        # Stream 3 is usually STREAM_MUSIC
        run_adb_cmd("media volume --stream 3 --set 5")
        time.sleep(1)
        
        # Check volume using dumpsys audio instead of media since some ROMs strip media get output
        code, out = run_adb_cmd('dumpsys audio | grep -i "\- STREAM_MUSIC" -A 5')
        
        if "5" in out and code == 0:
            reporter.add_result("Audio", "Media Volume Control", True, "Successfully set and read media volume via dumpsys")
        else:
            reporter.add_result("Audio", "Media Volume Control", False, f"Failed to verify media volume. Output: {out}")
            
    except Exception as e:
        reporter.add_result("Audio", "Media Volume Control", False, str(e))
        
    # 3. Speaker / Mic Hardware check via AudioFlinger
    try:
        _, out = run_adb_cmd("dumpsys media.audio_flinger")
        if "Hardware HAL" in out or "primary" in out.lower():
            reporter.add_result("Audio", "Audio HAL Initialization", True, "Audio HAL is loaded and responding")
        else:
            reporter.add_result("Audio", "Audio HAL Initialization", False, "Could not verify Audio HAL in dumpsys")
    except Exception as e:
        reporter.add_result("Audio", "Audio HAL Initialization", False, str(e))

    # 4. Microphone Recording Test (Phase 4)
    try:
        from framework.adb_helper import keep_screen_on
        keep_screen_on(True) # Ensure awake immediately before audio test
        
        logging.info("Starting Microphone Recording test...")
        # Check for multiple possible recording directories (Music is preference now)
        record_dirs = ["/sdcard/Music", "/sdcard/Recordings", "/sdcard/Download"]
        target_dir = "/sdcard/Music"
        for d in record_dirs:
            code, _ = run_adb_cmd(f"ls -d {d}")
            if code == 0:
                target_dir = d
                break

        _, out_before = run_adb_cmd(f"ls -R {target_dir} | wc -l")
        count_before = int(out_before.strip()) if out_before.strip().isdigit() else 0

        # --- Acoustic Loopback (A-L) Optimization ---
        # Note: Concurrent playback is blocked by OS on this device.
        # We will use Hardware Entropy Analysis instead.

        # Pre-grant permissions to common sound recorder packages
        recorder_pkgs = ["com.android.soundrecorder", "com.google.android.soundrecorder", "com.sec.android.app.voicenote"]
        for pkg in recorder_pkgs:
            run_adb_cmd(f"pm grant {pkg} android.permission.RECORD_AUDIO")
            run_adb_cmd(f"pm grant {pkg} android.permission.WRITE_EXTERNAL_STORAGE")
            run_adb_cmd(f"pm grant {pkg} android.permission.READ_EXTERNAL_STORAGE")

        # Launch Sound Recorder Intent
        run_adb_cmd("am start -a android.provider.MediaStore.RECORD_SOUND")
        time.sleep(3)
        
        # UI Interaction: 1. Bypass all Permission Dialogs & OOBE Overlays
        logging.info("Bypassing permission and OOBE dialogs...")
        for _ in range(8):
            found = False
            # Handles permissions, Got it, Next, etc.
            for btn_text in ["Allow", "Allow all", "WHILE USING THE APP", "Next", "OK", "AGREE", "Got it", "Continue", "Confirm", "CONFIRM", "允許", "使用時允許", "僅在主用時允許", "我知道了", "下一步", "繼續", "確定"]:
                btn = ui.d(textMatches=f"(?i){btn_text}")
                if btn.exists(timeout=1):
                    logging.info(f"Clicking audio popup: {btn_text}")
                    btn.click()
                    time.sleep(1.5)
                    found = True
            if not found: break

        # UI Interaction: 1.1 Handle "Recording list" view if it opens instead of recorder
        if ui.d(textMatches="(?i)Recording list").exists(timeout=2):
            logging.info("Detected 'Recording list' view, attempting to navigate to recorder...")
            nav_up = ui.d(descriptionMatches="(?i)Navigate up")
            if nav_up.exists:
                nav_up.click()
                time.sleep(2)
            else:
                ui.d.press("back")
                time.sleep(2)

        # UI Interaction: 2. Start Recording
        logging.info("Attempting to start recording...")
        start_button = None
        # ... (rest of start_button logic) ...
        # 1. Use the EXACT ID provided by user
        specific_id = "com.android.soundrecorder:id/recordButton"
        btn = ui.d(resourceId=specific_id)
        if btn.exists(timeout=2):
            start_button = btn
        
        # Fallback to common IDs if specific one fails
        if not start_button:
            start_ids = [".*record_button.*", ".*start_button.*", ".*btn_record.*", ".*shutter.*", ".*fab.*"]
            for res_id in start_ids:
                btn = ui.d(resourceIdMatches=res_id)
                if btn.exists(timeout=1):
                    start_button = btn
                    break
        
        # Fallback to Content Description
        if not start_button:
            for desc in ["Record", "Start", "錄製", "開始", "錄音"]:
                btn = ui.d(descriptionMatches=f"(?i){desc}")
                if btn.exists(timeout=1):
                    start_button = btn
                    break
        
        if start_button:
            logging.info(f"Clicking Start/Record button: {start_button.info.get('resourceName') or 'generic'}")
            start_button.click()
            time.sleep(1) # Small delay for UI
        else:
            logging.warning("Could not find Record button. Saving UI dump...")
            hierarchy = ui.d.dump_hierarchy()
            with open("/tmp/audio_recorder_ui.xml", "w") as f:
                f.write(hierarchy)

        # Record background noise for hardware verification
        logging.info("Recording 8s of background noise for hardware verification...")
        time.sleep(8) 
        
        # 3. Stop Recording
        logging.info("Attempting to stop/save recording...")
        stop_id = "com.android.soundrecorder:id/stopButton"
        btn = ui.d(resourceId=stop_id)
        stop_clicked = False # Fixed: Initialize before assignment
        if btn.exists(timeout=2):
            btn.click()
            logging.info("Clicked specific stopButton.")
            stop_clicked = True
        else:
            # Fallback
            stop_ids = [".*stop_button.*", ".*done_button.*", ".*save_button.*", ".*btn_stop.*", ".*check.*"]
            for res_id in stop_ids:
                btn = ui.d(resourceIdMatches=res_id)
                if btn.exists(timeout=1):
                    btn.click()
                    stop_clicked = True
                    break
        
        # Handle "Save recording?" dialog or "OK" confirmation
        time.sleep(1)
        for dialog_btn in ["Save", "OK", "儲存", "確定"]:
             btn = ui.d(textMatches=f"(?i){dialog_btn}")
             if btn.exists(timeout=1):
                 logging.info(f"Clicking dialog button: {dialog_btn}")
                 btn.click()
                 time.sleep(1)

        if not stop_clicked:
            for stop_text in ["Stop", "Done", "停止", "完成", "OK", "✔"]:
                btn = ui.d(textMatches=f"(?i){stop_text}")
                if btn.exists(timeout=1):
                    btn.click()
                    stop_clicked = True
                    break
        
        # 4. Verification: Look for recently created AMR/M4A/3GP files
        time.sleep(3) # Wait for filesystem sync
        # Find files modified in the last 2 minutes (+1 for safety)
        find_cmd = f"find {target_dir} -maxdepth 2 -mmin -2 -type f | grep -E 'amr|m4a|3gp|wav'"
        _, find_out = run_adb_cmd(find_cmd)
        
        if find_out.strip():
            latest_file = find_out.strip().split('\n')[-1]
            logging.info(f"Verification Success: Found new audio file: {latest_file}")
            
            # --- Entropy-Based Hardware Verification (PC Side) ---
            import subprocess
            host_tmp_path = "/tmp/audio_verify.amr"
            pull_cmd = f"adb pull {latest_file} {host_tmp_path}"
            subprocess.run(pull_cmd, shell=True, check=True, capture_output=True)
            
            try:
                with open(host_tmp_path, "rb") as f:
                    data = f.read(2000) # Read first 2KB
                    entropy_score = len(set(data))
                
                logging.info(f"Audio Entropy Score: {entropy_score} (Unique bytes in 2KB)")
                
                # Threshold: > 50 unique bytes indicates actual noise/signal vs static/silence
                if entropy_score > 50:
                    reporter.add_result("Audio", "Microphone Hardware Verification", True, f"PASS: Mic is alive (Entropy Score: {entropy_score})")
                else:
                    reporter.add_result("Audio", "Microphone Hardware Verification", False, f"FAIL: Mic detected as silent/static (Entropy Score: {entropy_score})")
            except Exception as analysis_err:
                reporter.add_result("Audio", "Microphone Hardware Verification", False, f"Analysis Error: {analysis_err}")
        else:
             # Check for permission controller as fallback
             current = ui.d.app_current()
             if "permissioncontroller" in current['package']:
                 reporter.add_result("Audio", "Microphone Recording", False, "Failed: Stuck on Permission Dialog")
             else:
                 reporter.add_result("Audio", "Microphone Recording", False, f"Failed: No new audio file found in {target_dir} (mmin -2)")
        
        ui.go_home()
        
    except Exception as e:
        reporter.add_result("Audio", "Microphone Recording", False, str(e))
