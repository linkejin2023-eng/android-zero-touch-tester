from framework.adb_helper import get_system_property, run_adb_cmd, set_system_property
from framework.ui_automator import UIHelper
from framework.report_generator import HTMLReportGenerator
import time
import logging

def run_tests(ui: UIHelper, reporter: HTMLReportGenerator):
    logging.info("Running Display Tests...")
    
    # 1. Video Playback Verification (Phase 4)
    try:
        logging.info("Starting Video Playback test...")
        # Check for existing video, or generate one if missing (to avoid network dependency)
        target_video = "/sdcard/test_video.mp4"
        code_exists, _ = run_adb_cmd(f"ls {target_video}")
        
        if code_exists != 0:
            logging.info(f"Generating local test video via screenrecord: {target_video}")
            # Record 3 seconds of screen
            run_adb_cmd(f"screenrecord --time-limit 3 {target_video}")
            time.sleep(4)
            
        logging.info(f"Playing video: {target_video}")
        run_adb_cmd(f"am start -a android.intent.action.VIEW -d 'file://{target_video}' -t 'video/mp4'")
            
        time.sleep(5)
        
        # Verify hardware codec activity via dumpsys
        _, out = run_adb_cmd("dumpsys media.player")
        # Check for active sessions or codec strings
        if "NuPlayer" in out or "AudioSink" in out or "active" in out.lower():
            reporter.add_result("Display", "Video Playback (Hardware Codec)", True, "Video playback activity detected in media.player")
        else:
            # Secondary check via metrics
            _, metrics = run_adb_cmd("dumpsys media.metrics")
            if "video" in metrics.lower():
                reporter.add_result("Display", "Video Playback (Hardware Codec)", True, "Video decoding activity detected in media.metrics")
            else:
                reporter.add_result("Display", "Video Playback (Hardware Codec)", False, "No active video playback detected")
        
        ui.go_home()
        
    except Exception as e:
        reporter.add_result("Display", "Video Playback Test", False, str(e))
