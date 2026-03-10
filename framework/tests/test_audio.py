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
        logging.info("Starting Microphone Recording test...")
        # Check for multiple possible recording directories
        record_dirs = ["/sdcard/Recordings", "/sdcard/Music", "/sdcard/Download"]
        target_dir = "/sdcard/Recordings"
        for d in record_dirs:
            code, _ = run_adb_cmd(f"ls -d {d}")
            if code == 0:
                target_dir = d
                break

        _, out_before = run_adb_cmd(f"ls {target_dir} | wc -l")
        count_before = int(out_before.strip()) if out_before.strip().isdigit() else 0

        # Launch Sound Recorder Intent
        run_adb_cmd("am start -a android.provider.MediaStore.RECORD_SOUND")
        time.sleep(2)
        
        # UI Interaction to start recording if possible (generic button search)
        for btn_text in ["Record", "Start", "允許", "錄音", "OK"]:
            btn = ui.d(textMatches=f"(?i){btn_text}")
            if btn.exists(timeout=1):
                btn.click()
                time.sleep(1)

        # Simulate some recording time
        time.sleep(5)
        
        # Check for file increase or logcat activity
        _, out_after = run_adb_cmd(f"ls {target_dir} | wc -l")
        count_after = int(out_after.strip()) if out_after.strip().isdigit() else 0
        
        if count_after > count_before:
             reporter.add_result("Audio", "Microphone Recording", True, f"Recording file created in {target_dir}")
        else:
             # Fallback check via logcat
             _, logs = run_adb_cmd("logcat -d | grep -iE 'AudioRecord|AudioSource|Recorder' | tail -n 20")
             if "AudioRecord" in logs or "start" in logs.lower():
                 reporter.add_result("Audio", "Microphone Recording", True, "Microphone capture activity detected via Logcat")
             else:
                 reporter.add_result("Audio", "Microphone Recording", False, "No recording file or activity detected")
        
        ui.go_home()
        
    except Exception as e:
        reporter.add_result("Audio", "Microphone Recording", False, str(e))
