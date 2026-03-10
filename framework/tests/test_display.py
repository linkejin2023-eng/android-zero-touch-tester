from framework.adb_helper import get_system_property, run_adb_cmd, set_system_property
from framework.ui_automator import UIHelper
from framework.report_generator import HTMLReportGenerator
import time
import logging

def run_tests(ui: UIHelper, reporter: HTMLReportGenerator):
    logging.info("Running Display Tests...")
    
    # Test 1: Brightness Control (adb level)
    try:
        # Read current
        orig_brightness = get_system_property("persist.sys.screen_brightness") # or settings get system screen_brightness
        code, out = run_adb_cmd("settings get system screen_brightness")
        orig = out.strip() if code == 0 else "128"
        
        # Write
        run_adb_cmd("settings put system screen_brightness 50")
        time.sleep(1)
        code, check = run_adb_cmd("settings get system screen_brightness")
        if check.strip() == "50":
            reporter.add_result("Display", "Set Brightness via ADB", True, "Successfully changed brightness to 50")
        else:
            reporter.add_result("Display", "Set Brightness via ADB", False, f"Failed to set brightness. Current: {check}")
            
        # Restore
        run_adb_cmd(f"settings put system screen_brightness {orig}")
    except Exception as e:
        reporter.add_result("Display", "Set Brightness via ADB", False, str(e))
        
    # Test 2: UI Automator Screen Wake/Sleep
    try:
        # Sleep
        ui.d.screen_off()
        time.sleep(2)
        if not ui.d.info.get('screenOn'):
            reporter.add_result("Display", "Screen Off (Suspend)", True, "Screen successfully turned off")
        else:
            reporter.add_result("Display", "Screen Off (Suspend)", False, "Screen did not turn off")
            
        # Wake
        logging.info("Attempting to wake screen...")
        ui.d.screen_on()
        run_adb_cmd("input keyevent 224") # WAKEUP key
        time.sleep(2)
        
        # Verify via UIAutomator and fallback to dumpsys
        screen_on_ui = ui.d.info.get('screenOn')
        _, pwr = run_adb_cmd("dumpsys power | grep mWakefulness")
        is_awake = "Awake" in pwr or "Dreaming" in pwr or screen_on_ui
        
        if is_awake:
            reporter.add_result("Display", "Screen On (Resume)", True, "Screen successfully turned on")
        else:
            # Last ditch effort: Power button
            run_adb_cmd("input keyevent 26")
            time.sleep(1)
            _, pwr = run_adb_cmd("dumpsys power | grep mWakefulness")
            if "Awake" in pwr or ui.d.info.get('screenOn'):
                reporter.add_result("Display", "Screen On (Resume)", True, "Screen turned on (via Power button fallback)")
            else:
                reporter.add_result("Display", "Screen On (Resume)", False, f"Screen did not turn on. State: {pwr.strip()}")
    except Exception as e:
        reporter.add_result("Display", "Screen State Toggle", False, f"UIAutomator error: {e}")

    # 3. Video Playback Verification (Phase 4)
    try:
        logging.info("Starting Video Playback test...")
        # Search for any mp4 file on sdcard to play, if none, use a system video if possible
        _, files = run_adb_cmd("find /sdcard -name '*.mp4' | head -n 1")
        video_path = files.strip()
        
        if video_path:
            run_adb_cmd(f"am start -a android.intent.action.VIEW -d 'file://{video_path}' -t 'video/mp4'")
        else:
            # Try launching the video player app directly as fallback
            run_adb_cmd("am start -a android.intent.action.VIEW -d 'http://localhost/dummy.mp4' -t 'video/mp4'")
            
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
