import sys
import logging
import time
import argparse
from framework.adb_helper import wait_for_device, get_system_property, run_adb_cmd
from framework.ui_automator import UIHelper
from framework.report_generator import HTMLReportGenerator
from framework.tests import test_display, test_audio, test_camera, test_connectivity, test_sensors_power
from framework.tests import test_touch, test_sensors_advanced, test_housekeeper, test_buttons, test_nfc, test_gps

from framework.flash_manager import FlashManager

def main():
    parser = argparse.ArgumentParser(description="Android Sanity Test Automation Framework")
    parser.add_argument("--flash", type=str, help="Path to firmware ZIP to flash before testing")
    parser.add_argument("--oobe", action="store_true", help="Run only OOBE bypass and ADB enablement (manual debug)")
    parser.add_argument("--sku", type=str, choices=["gms", "china"], default="gms", help="Product SKU type for OOBE sequence (default: gms)")
    parser.add_argument("--skip-tests", action="store_true", help="Only flash/OOBE, skip tests")
    args = parser.parse_args()

    logging.info("--- Starting Android Sanity Test Automation ---")

    # --- Phase 0: Flashing ---
    if args.flash:
        logging.info(f"Flash requested with: {args.flash}")
        fm = FlashManager(args.flash)
        if not fm.flash():
            logging.error("Flashing failed. Aborting.")
            sys.exit(1)
        args.oobe = True # Force OOBE bypass after flash

    if args.oobe:
        # After flashing or manual request, wait for device to boot into OOBE and bypass it
        logging.info(f"Entering OOBE Bypass synchronization loop (SKU: {args.sku})...")
        try:
            from hid_gadget import run_oobe_bypass
        except ImportError as e:
            logging.error(f"Failed to import oobe_bypass_script: {e}")
            sys.exit(1)
            
        if not run_oobe_bypass(sku=args.sku, timeout=300):
            logging.error("OOBE Bypass failed or timed out.")
            sys.exit(1)

        if args.skip_tests:
            logging.info("OOBE Bypass successful. Tests skipped as per --skip-tests flag.")
            return

    # --- Phase 1: Environment Readiness ---
    # After bypass, ADB should be authorized and ready
    if not wait_for_device(timeout=60):
        # If skip-tests wasn't set, we expect ADB to be ready here
        logging.error("No authorized ADB device detected after OOBE bypass.")
        sys.exit(1)
        
    # Pro-actively bypass Setup Wizard for newly flashed builds (via ADB as backup/second layer)
    logging.info("Ensuring Setup Wizard is bypassed (ADB layer)...")
    run_adb_cmd("settings put global device_provisioned 1")
    run_adb_cmd("settings put secure user_setup_complete 1")
    run_adb_cmd("am start -c android.intent.category.HOME -a android.intent.action.MAIN")
    time.sleep(2)

    if args.skip_tests:
        logging.info("Tests skipped as per --skip-tests flag.")
        return

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
