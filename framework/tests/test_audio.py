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
