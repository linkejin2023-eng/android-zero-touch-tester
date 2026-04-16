import sys
import logging
import time
import argparse
import yaml
from framework.adb_helper import wait_for_device, get_system_property, run_adb_cmd
from framework.ui_automator import UIHelper
from framework.report_generator import HTMLReportGenerator
from framework.tests import test_audio, test_camera, test_connectivity, test_sensors_power
from framework.tests import test_sensors_advanced, test_nfc, test_gps, test_reboot, test_lifecycle, test_firmware

from framework.flash_manager import FlashManager

def main():
    parser = argparse.ArgumentParser(description="Android Sanity Test Automation Framework")
    parser.add_argument("--flash", type=str, help="Path to firmware ZIP to flash before testing")
    parser.add_argument("--oobe", action="store_true", help="Bypass OOBE and then proceed to full tests")
    parser.add_argument("--oobe-only", action="store_true", help="Run only OOBE bypass and ADB enablement, then stop (Manual debug)")
    parser.add_argument("--sku", type=str, choices=["gms", "china"], default="gms", help="Product SKU type for OOBE sequence (default: gms)")
    parser.add_argument("--skip-tests", action="store_true", help="Abort after Flash/OOBE, do not run test cases")
    parser.add_argument("--only-tests", action="store_true", help="Skip flash/OOBE/Provisioning, run tests directly on established device")
    parser.add_argument("--no-wipe", action="store_true", help="Skip userdata wipe during flashing (simulated OTA)")
    parser.add_argument("--factory-reset", action="store_true", help="Trigger Factory Reset via HID sequence (Expert only)")
    parser.add_argument("--config-dir", type=str, help="Directory to load build_info.json and other configs (Workspace path)")
    parser.add_argument("--report-dir", type=str, default="reports", help="Directory to save the HTML report (default: reports)")
    parser.add_argument("--build", type=str, default="Unknown", help="Build version number for report naming [Auto-detected if omitted]")
    parser.add_argument("--type", type=str, default="user", choices=["user", "userdebug"], help="Build variant for report naming [Auto-detected if omitted]")
    args = parser.parse_args()

    # --- Phase -1: Emergency Factory Reset (Expert only) ---
    if args.factory_reset:
        logging.info("--- SHUTDOWN SEQUENCE: FACTORY RESET REQUESTED ---")
        logging.warning("This will wipe the device and ADB authorization will be lost.")
        from hid_gadget import oobe_bypass_script, aoa_driver
        driver = aoa_driver.AOADriver()
        if driver.find_device():
            if driver.switch_to_accessory_mode():
                driver.register_hid(1, aoa_driver.KB_REPORT_DESC)
                driver.register_hid(2, aoa_driver.CONSUMER_REPORT_DESC)
                bypass = oobe_bypass_script.OOBEBypass(driver)
                bypass.reset_device_to_factory_settings()
                logging.info("Factory Reset sequence sent. Device will reboot soon.")
                return
        logging.error("Failed to find HID device for factory reset.")
        sys.exit(1)

    logging.info("--- Starting Android Sanity Test Automation ---")

    # --- Phase 0: Flashing ---
    if args.flash:
        logging.info(f"Flash requested with: {args.flash} (No-Wipe: {args.no_wipe})")
        fm = FlashManager(args.flash, no_wipe=args.no_wipe)
        if not fm.flash():
            logging.error("Flashing failed. Aborting.")
            sys.exit(1)
        args.oobe = True # Force OOBE bypass after flash

    if args.oobe or args.oobe_only:
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

        if args.oobe_only or args.skip_tests:
            logging.info("OOBE/ADB Setup successful. Stopping as requested.")
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
    reporter = HTMLReportGenerator(output_dir=args.report_dir)
    
    # Collect Device Info
    sku_raw = get_system_property("ro.boot.sku")
    build_type_raw = get_system_property("ro.build.type") # 自動偵測 user/userdebug
    
    # 智慧校正：如果偵測到的型態與參數不符，以機台實際型態為準
    if build_type_raw in ["user", "userdebug"]:
        args.type = build_type_raw

    # Load System Configurations from configs/
    import json
    import os
    
    def load_json_config(filename, default=None):
        # 1. 優先從 Workspace (args.config_dir) 讀取
        if args.config_dir:
            path = os.path.join(args.config_dir, filename)
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        logging.info(f"Loaded {filename} from workspace: {path}")
                        return json.load(f)
                except Exception as e:
                    logging.warning(f"Error loading {path}: {e}")

        # 2. 如果 Workspace 找不到，回退到全域 configs/
        path = os.path.join("configs", filename)
        try:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logging.warning(f"Could not load {path}: {e}")
        return default or {}

    build_info = load_json_config("build_info.json")
    hw_specs_data = load_json_config("hardware_specs.json")
    ui_selectors_data = load_json_config("ui_selectors.json")

    sku_map = build_info.get("sku_map", {})
    sku_label = sku_map.get(sku_raw, sku_raw)
    
    # --- Diagnostic Info Collection ---
    _, selinux_status = run_adb_cmd("getenforce")
    selinux_status = selinux_status.strip()
    
    # 區分「當前權限」與「系統檔案」
    _, id_out = run_adb_cmd("id")
    is_active_root = "uid=0(root)" in id_out
    
    _, su_check = run_adb_cmd("which su")
    has_su = "not found" not in su_check.lower() and su_check.strip() != ""
    
    _, kernel_ver = run_adb_cmd("uname -r -v")
    
    device_info = {
        "Model": get_system_property("ro.product.model"),
        "Brand": get_system_property("ro.product.brand"),
        "Variant": args.type,
        "Android Version": get_system_property("ro.build.version.release"),
        "Build Number": get_system_property("ro.build.display.id"),
        "Fingerprint": get_system_property("ro.build.fingerprint"),
        "Security Patch": get_system_property("ro.build.version.security_patch"),
        "GMS Version": get_system_property("ro.com.google.gmsversion"),
        "Kernel": kernel_ver.strip(),
        "Serial": get_system_property("ro.serialno"),
        "SKU ID": f"{sku_raw} ({sku_label})" if sku_label != sku_raw else sku_raw,
        "OEM Lock": "Locked" if get_system_property("ro.boot.flash.locked") == "1" else "Unlocked",
        "SELinux": selinux_status,
        "ADB Root": "Active (root)" if is_active_root else "Inactive (shell)",
        "SU Binary": "Present" if has_su else "Not Found"
    }
    reporter.set_device_info(device_info)
    
    logging.info(f"Target Device: {device_info['Brand']} {device_info['Model']}")
    
    # --- Smart Build ID Normalization (For accurate report naming) ---
    final_build_id = args.build
    if final_build_id == "Unknown":
        raw_display_id = device_info.get("Build Number", "Unknown")
        parts = raw_display_id.split()
        if len(parts) > 1:
            # Skip signature suffix if present
            final_build_id = parts[-2] if "keys" in parts[-1] else parts[-1]
        else:
            final_build_id = raw_display_id

    # Initialize UI Automator
    try:
        ui = UIHelper()
    except Exception as e:
        reporter.add_result("System", "UIAutomator Initialization", False, f"Failed to start uiautomator2 agent: {e}")
        reporter.finalize(time.time() - start_time, version=final_build_id, variant=args.type)
        sys.exit(1)
        
    reporter.add_result("System", "ADB & UIAutomator Connection", True, "Successfully connected to device and injected test agents.")
    
    # Ensure screen is on and won't sleep during tests
    from framework.adb_helper import keep_screen_on, get_stay_on_state, set_stay_on_state
    
    # 1. Backup original state
    original_stay_on = get_stay_on_state()
    
    # 2. Force screen on and unlock
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
        
        # 安全預檢：任何一項不符即視為 Insecure
        if is_debuggable or is_active_root or has_su or selinux_status.lower() != "enforcing":
            status_msg = f"Security Preflight: Debuggable={is_debuggable}, SELinux={selinux_status}, ADB_Root={is_active_root}, SU={has_su}"
            
            # 只有開發版 (userdebug) 允許繞過。
            # 如果是 User build，即便偵測到後門也必須攔截，因為這代表機台狀態不正確。
            if args.type == "userdebug":
                logging.warning(f"Insecure Environment detected (Debuggable or SELinux), but proceeding as requested.")
                reporter.add_result("System", "Security Preflight", True, 
                                    f"WARNING: {status_msg}", 
                                    status_override="SKIP")
            else:
                reporter.add_result("System", "Security Preflight", False, 
                                    f"ERROR: {status_msg}", 
                                    status_override="ERROR")
                logging.error(f"Security Check Failed: {status_msg}")
                logging.error("CRITICAL: Backdoor or Insecure configuration detected on a USER build!")
                logging.error("Aborting tests to ensure validation environment matches release standards.")
                reporter.finalize(time.time() - start_time, version=final_build_id, variant=args.type)
                sys.exit(1)
        else:
            reporter.add_result("System", "Security Preflight", True, f"Environment OK (SELinux: {selinux_status})")
            logging.info("Security Preflight Passed.")

        # --- Execute Test Modules ---
        logging.info("Executing configured test suites...")
        mods = config.get("modules", {})
        
        # Initialize metrics in case lifecycle is skipped or reset fails
        baseline_uptime, baseline_files = 0.0, 0
        final_uptime, final_files = 0.0, 0
        
        def should_run(mod_name):
            return mods.get(mod_name, True)
        
        # Extract categorized specs from new config structure
        hw_specs = hw_specs_data.get("hardware", {})
        ui_selectors = ui_selectors_data.get("ui_selectors", {})
        fw_validations = build_info.get("validations", [])
        
        # Priority: Reboot & Firmware
        if should_run("reboot"):
            test_reboot.run_tests(ui, reporter)
        
        if should_run("firmware"):
            test_firmware.run_tests(ui, reporter, validations=fw_validations)
        
        # Phase 1
        if should_run("audio"):
            test_audio.run_tests(ui, reporter, specs=hw_specs, selectors=ui_selectors)
        if should_run("camera"):
            test_camera.run_tests(ui, reporter, specs=hw_specs, selectors=ui_selectors)
        if should_run("connectivity"):
            # Pass network config if available, otherwise tests will fallback or fail
            net_config = config.get("network", {})
            test_connectivity.run_tests(ui, reporter, 
                                        ssid=net_config.get("wifi_ssid"), 
                                        password=net_config.get("wifi_pass"),
                                        specs=hw_specs,
                                        selectors=ui_selectors)
        if should_run("sensors_power"):
            test_sensors_power.run_tests(ui, reporter)
        
        # Phase 2
        if should_run("sensors_advanced"):
            test_sensors_advanced.run_tests(ui, reporter)
        if should_run("nfc"):
            test_nfc.run_tests(ui, reporter)
        if should_run("gps"):
            test_gps.run_tests(ui, reporter)
        # --- Final Metric Collection (Pre-Reset) ---
        if config.get('modules', {}).get('auto_factory_reset', False):
            baseline_uptime, baseline_files = test_lifecycle.get_metrics()
            logging.info(f"Baseline captured: {baseline_files} files, {baseline_uptime:.2f}h uptime")
    finally:
        # Restore original screen sleep settings after all tests finish
        logging.info("Tests finished. Restoring original device state...")
        if 'original_stay_on' in locals():
            set_stay_on_state(original_stay_on)
        else:
            # Fallback if backup failed
            keep_screen_on(False)
    
    # Generate Final Report

    # --- Phase 99: Final Lifecycle (Auto-Reset & Verify) ---
    if config.get('modules', {}).get('auto_factory_reset', False):
        logging.info("--- FULL CYCLE: Starting Automated Factory Reset & Verification ---")
        from hid_gadget import oobe_bypass_script, aoa_driver, run_oobe_bypass
        driver = aoa_driver.AOADriver()
        if driver.find_device():
            if driver.switch_to_accessory_mode():
                driver.register_hid(1, aoa_driver.KB_REPORT_DESC)
                driver.register_hid(2, aoa_driver.CONSUMER_REPORT_DESC)
                bypass = oobe_bypass_script.OOBEBypass(driver)
                bypass.reset_device_to_factory_settings()
                
                logging.info("Reset triggered. Waiting 60s for device to reach OOBE...")
                time.sleep(60)
                
                logging.info("Attempting OOBE Bypass & ADB Enablement after reset...")
                if run_oobe_bypass(sku=args.sku, timeout=600):
                    logging.info("Bypass successful. Waiting for ADB...")
                    if wait_for_device(timeout=60):
                        # Re-provision/Setup Wizard bypass for sanity
                        run_adb_cmd("settings put global device_provisioned 1")
                        run_adb_cmd("settings put secure user_setup_complete 1")
                        run_adb_cmd("am start -c android.intent.category.HOME -a android.intent.action.MAIN")
                        time.sleep(5)
                        
                        logging.info("Running Final Post-Reset Audit...")
                        # Re-init UI helper as the agent was wiped
                        ui = UIHelper()
                        final_uptime, final_files = test_lifecycle.get_metrics()
                        
                        summary_msg = (f"Full-cycle reset verified. "
                                       f"Uptime: {baseline_uptime:.2f}h -> {final_uptime:.2f}h, "
                                       f"Files: {baseline_files} -> {final_files}")
                        
                        is_success = (final_files == 0)
                        reporter.add_result("System", "Factory Reset Lifecycle", is_success, summary_msg)
                    else:
                        reporter.add_result("System", "Factory Reset Lifecycle", False, "Timeout waiting for ADB after reset.")
                else:
                    reporter.add_result("System", "Factory Reset Lifecycle", False, "OOBE Bypass failed after reset.")
        else:
            logging.error("Failed to find HID device for auto-reset.")

    # --- Final Report Generation (After all lifecycle phases) ---
    duration = time.time() - start_time
    
    # 智慧命名：如果編號為 Unknown，自動從機台資訊中提取
    final_build_id = args.build
    if final_build_id == "Unknown":
        # 嘗試從 ro.build.display.id 提取，避開末尾的 release-keys / test-keys
        raw_display_id = device_info.get("Build Number", "Unknown")
        parts = raw_display_id.split()
        if len(parts) > 1:
            # 檢查最後一項是否為簽章標籤 (例如 release-keys)
            if "keys" in parts[-1] and len(parts) > 1:
                final_build_id = parts[-2]
            else:
                final_build_id = parts[-1]
        else:
            final_build_id = raw_display_id

    report_path = reporter.finalize(duration, version=final_build_id, variant=args.type)
    
    # --- Final Result Assessment (Industrial Logic) ---
    # 定義環境敏感豁免清單 (這幾項 Fail 不會影響 CI 退出狀態，因為環境受限)
    SOFT_FAILURE_LIST = ["GPS Antenna Signal", "Tag Read Verification", "WiFi Association"]
    
    total_failures = reporter.summary.get("failed", 0) + reporter.summary.get("error", 0)
    
    # 找出有多少失敗是來自於「非環境」因素
    exemption_count = 0
    for res in reporter.results:
        if res["status"] in ["FAIL", "ERROR"] and res["test_name"] in SOFT_FAILURE_LIST:
            exemption_count += 1
            
    effective_failures = total_failures - exemption_count
    
    logging.info(f"--- Tests Completed in {duration:.1f}s ---")
    logging.info(f"Summary: Total_Failures={total_failures}, Env_Exemptions={exemption_count}, Effective_Failures={effective_failures}")
    logging.info(f"Report location: {report_path}")

    # CI 誠實回傳值：只有當有「非環境因素」的失敗時，才回報 1 (FAIL)
    if effective_failures > 0:
        import sys
        sys.exit(1)
    else:
        import sys
        sys.exit(0)

if __name__ == "__main__":
    main()
