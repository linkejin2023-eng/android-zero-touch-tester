import sys
import logging
import time
from framework.adb_helper import wait_for_device, get_system_property, run_adb_cmd
from framework.ui_automator import UIHelper
from framework.report_generator import HTMLReportGenerator

from framework.tests import test_display, test_audio, test_camera, test_connectivity, test_sensors_power
from framework.tests import test_touch, test_sensors_advanced, test_housekeeper, test_buttons, test_nfc, test_gps

def main():
    logging.info("--- Starting Android Sanity Test Automation ---")
    
    if not wait_for_device(timeout=10):
        logging.error("No device detected. Did you run the Setup Wizard bypass script first?")
        sys.exit(1)
        
    # Pro-actively bypass Setup Wizard for newly flashed builds
    logging.info("Ensuring Setup Wizard is bypassed...")
    run_adb_cmd("settings put global device_provisioned 1")
    run_adb_cmd("settings put secure user_setup_complete 1")
    run_adb_cmd("am start -c android.intent.category.HOME -a android.intent.action.MAIN")
    time.sleep(2)

    start_time = time.time()
        
    # Initialize Reporter
    reporter = HTMLReportGenerator()
    
    # Collect Device Info
    device_info = {
        "Model": get_system_property("ro.product.model"),
        "Brand": get_system_property("ro.product.brand"),
        "Android Version": get_system_property("ro.build.version.release"),
        "Build Number": get_system_property("ro.build.display.id"),
        "Serial": get_system_property("ro.serialno")
    }
    reporter.set_device_info(device_info)
    
    logging.info(f"Target Device: {device_info['Brand']} {device_info['Model']}")
    
    # Initialize UI Automator
    try:
        ui = UIHelper()
    except Exception as e:
        reporter.add_result("System", "UIAutomator Initialization", False, f"Failed to start uiautomator2 agent: {e}")
        reporter.finalize(time.time() - start_time)
        sys.exit(1)
        
    reporter.add_result("System", "ADB & UIAutomator Connection", True, "Successfully connected to device and injected test agents.")
    
    # --- Execute Test Modules ---
    logging.info("Executing test suites...")
    
    # Phase 1
    test_display.run_tests(ui, reporter)
    test_audio.run_tests(ui, reporter)
    test_camera.run_tests(ui, reporter)
    test_connectivity.run_tests(ui, reporter)
    test_sensors_power.run_tests(ui, reporter)
    
    # Phase 2
    test_touch.run_tests(ui, reporter)
    test_sensors_advanced.run_tests(ui, reporter)
    test_housekeeper.run_tests(ui, reporter)
    test_buttons.run_tests(ui, reporter)
    test_nfc.run_tests(ui, reporter)
    test_gps.run_tests(ui, reporter)
    
    # Generate Final Report
    duration = time.time() - start_time
    report_path = reporter.finalize(duration)
    
    logging.info(f"--- Tests Completed in {duration:.1f}s ---")
    logging.info(f"Report location: {report_path}")

if __name__ == "__main__":
    main()
