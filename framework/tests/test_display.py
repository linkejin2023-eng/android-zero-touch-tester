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
        ui.d.screen_on()
        time.sleep(2)
        if ui.d.info.get('screenOn'):
            reporter.add_result("Display", "Screen On (Resume)", True, "Screen successfully turned on")
        else:
            reporter.add_result("Display", "Screen On (Resume)", False, "Screen did not turn on")
    except Exception as e:
        reporter.add_result("Display", "Screen State Toggle", False, f"UIAutomator error: {e}")
