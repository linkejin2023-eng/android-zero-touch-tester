import sys
import logging
import time
import argparse
import yaml
from framework.adb_helper import wait_for_device, get_system_property, run_adb_cmd
from framework.ui_automator import UIHelper
from framework.report_generator import HTMLReportGenerator
from framework.tests import test_display, test_audio, test_camera, test_connectivity, test_sensors_power
from framework.tests import test_sensors_advanced, test_nfc, test_gps, test_reboot

from framework.flash_manager import FlashManager

def main():
    parser = argparse.ArgumentParser(description="Android Sanity Test Automation Framework")
    parser.add_argument("--flash", type=str, help="Path to firmware ZIP to flash before testing")
    parser.add_argument("--oobe", action="store_true", help="Run only OOBE bypass and ADB enablement (manual debug)")
    parser.add_argument("--sku", type=str, choices=["gms", "china"], default="gms", help="Product SKU type for OOBE sequence (default: gms)")
    parser.add_argument("--skip-tests", action="store_true", help="Only flash/OOBE, skip tests")
    parser.add_argument("--only-tests", action="store_true", help="Skip flash/OOBE/Provisioning, run tests directly on established device")
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
        logging.info("--- Stage 1: HID/AOA OOBE Bypass (No ADB required) ---")
        logging.info(f"Entering HID synchronization loop (SKU: {args.sku})...")
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
        logging.error("No authorized ADB device detected after OOBE bypass.")
        if args.only_tests:
            logging.warning("=== HINT ===")
            logging.warning("It seems ADB is disabled. If the device is on the 'Welcome' screen,")
            logging.warning("please run WITHOUT --only-tests (or with --oobe) to enable ADB first.")
        sys.exit(1)
        
    # Pro-actively bypass Setup Wizard for newly flashed builds (via ADB as backup/second layer)
    if not args.only_tests:
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
        "Serial": get_system_property("ro.serialno"),
        "SKU ID": get_system_property("ro.boot.sku")
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
    
    # Ensure screen is on and won't sleep during tests
    from framework.adb_helper import keep_screen_on
    keep_screen_on(True)

    # --- Config Driven Preflight & Execution ---
    # Load Configuration
    config = {}
    try:
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
        logging.info("Configuration loaded from config.yaml")
    except Exception as e:
        logging.warning(f"Failed to load config.yaml ({e}), using default ALL enabled configuration.")
        config = {"modules": {}}

    try:
        # Security Preflight Checks
        logging.info("Running Security Preflight Checks...")
        
        is_debuggable = get_system_property("ro.debuggable") == "1"
        _, selinux_status = run_adb_cmd("getenforce")
        selinux_status = selinux_status.strip()
        _, su_check = run_adb_cmd("which su")
        
        is_rooted = "not found" not in su_check.lower() and su_check.strip() != ""
        
        if is_debuggable or is_rooted or selinux_status.lower() != "enforcing":
            reporter.add_result("System", "Security Preflight", False, 
                                f"Insecure Environment! ro.debuggable={is_debuggable}, SELinux={selinux_status}, Rooted={is_rooted}", 
                                status_override="ERROR")
            logging.error(f"Security Check Failed: Debuggable={is_debuggable}, SELinux={selinux_status}, Rooted={is_rooted}")
            logging.error("Aborting tests due to compromised runtime environment (False-Positive Risk).")
            reporter.finalize(time.time() - start_time)
            sys.exit(1)
        else:
            reporter.add_result("System", "Security Preflight", True, f"Environment OK (SELinux: {selinux_status})")
            logging.info("Security Preflight Passed.")

        # --- Execute Test Modules ---
        logging.info("Executing configured test suites...")
        mods = config.get("modules", {})
        
        def should_run(mod_name):
            return mods.get(mod_name, True)
        
        # Priority: Reboot
        if should_run("reboot"):
            test_reboot.run_tests(ui, reporter)
        
        # Phase 1
        if should_run("display"):
            test_display.run_tests(ui, reporter)
        if should_run("audio"):
            test_audio.run_tests(ui, reporter)
        if should_run("camera"):
            test_camera.run_tests(ui, reporter)
        if should_run("connectivity"):
            # Pass network config if available, otherwise tests will fallback or fail
            net_config = config.get("network", {})
            test_connectivity.run_tests(ui, reporter, ssid=net_config.get("wifi_ssid"), password=net_config.get("wifi_pass"))
        if should_run("sensors_power"):
            test_sensors_power.run_tests(ui, reporter)
        
        # Phase 2
        if should_run("sensors_advanced"):
            test_sensors_advanced.run_tests(ui, reporter)
        if should_run("nfc"):
            test_nfc.run_tests(ui, reporter)
        if should_run("gps"):
            test_gps.run_tests(ui, reporter)
    finally:
        # Restore screen sleep settings after all tests finish
        logging.info("Tests finished. Restoring screen sleep settings...")
        keep_screen_on(False)
    
    # Generate Final Report
    duration = time.time() - start_time
    report_path = reporter.finalize(duration)
    
    logging.info(f"--- Tests Completed in {duration:.1f}s ---")
    logging.info(f"Report location: {report_path}")

if __name__ == "__main__":
    main()
