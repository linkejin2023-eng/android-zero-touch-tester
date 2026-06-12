import sys
import logging
import time
import argparse
import os
import json
import yaml
from framework.adb_helper import wait_for_device, get_system_property, run_adb_cmd
from framework.ui_automator import UIHelper
from framework.report_generator import HTMLReportGenerator
from framework.tests import (
    test_audio, test_camera, test_connectivity, test_sensors,
    test_nfc, test_gps, test_reboot, test_lifecycle, test_firmware
)

from framework.flash_manager import FlashManager

VERSION = "2.2.1"

def main():
    # Initialize logging first to ensure visibility
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logging.info(f"--- Starting Android Sanity Test Automation v{VERSION} ---")
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
    parser.add_argument("--profile", type=str, default="full_smoke", help="Testing profile name or path (default: full_smoke)")
    parser.add_argument("--serial", type=str, help="Target device serial number")
    args = parser.parse_args()

    # Set target serial globally
    from framework.adb_helper import set_global_serial
    set_global_serial(args.serial)

    # --- Phase -1: Emergency Factory Reset (Expert only) ---
    if args.factory_reset:
        logging.info("--- SHUTDOWN SEQUENCE: FACTORY RESET REQUESTED ---")
        logging.warning("This will wipe the device and ADB authorization will be lost.")
        from hid_gadget import oobe_bypass_script, aoa_driver
        driver = aoa_driver.AOADriver(serial=args.serial)
        if driver.find_device(serial=args.serial):
            if driver.switch_to_accessory_mode():
                driver.register_hid(1, aoa_driver.KB_REPORT_DESC)
                driver.register_hid(2, aoa_driver.CONSUMER_REPORT_DESC)
                bypass = oobe_bypass_script.OOBEBypass(driver)
                bypass.reset_device_to_factory_settings()
                logging.info("Factory Reset sequence sent. Device will reboot soon.")
                return
        logging.error("Failed to find HID device for factory reset.")
        sys.exit(1)

    # --- Config Driven Preflight & Execution ---
    # 1. Load Global Environment Config
    config = {}
    try:
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
        logging.info("Configuration loaded from config.yaml")
    except Exception as e:
        logging.warning(f"Failed to load config.yaml ({e}), using default thresholds.")
        config = {}

    # 2. Load Testing Profile (Scope & Exclusions)
    profile_data = {"modules": {}, "exclude_items": []}
    profile_input = args.profile
    if profile_input.endswith(".yaml") or "/" in profile_input:
        profile_path = profile_input
    else:
        profile_path = os.path.join("configs", "profiles", f"{profile_input}.yaml")

    try:
        if os.path.exists(profile_path):
            with open(profile_path, "r") as f:
                profile_data = yaml.safe_load(f)
            logging.info(f"Testing profile loaded: {profile_path}")
        else:
            logging.warning(f"Profile {profile_path} not found. Running all modules by default.")
    except Exception as e:
        logging.error(f"Error loading profile {profile_path}: {e}")

    # Merge profile modules into global config for execution
    config["modules"] = profile_data.get("modules", {})
    config["exclude_items"] = profile_data.get("exclude_items", [])

    # --- Phase 0: Flashing ---
    if args.flash:
        logging.info(f"--- Stage 0: Firmware Flashing (Target: {args.serial}) ---")
        # Use args.flash path directly, fallback to config only if needed (though args.flash is the value here)
        flash_zip = args.flash
        from framework.flash_manager import FlashManager
        fm = FlashManager(flash_zip, no_wipe=args.no_wipe, serial=args.serial)
        if not fm.flash():
            logging.error("Flashing failed. Aborting.")
            sys.exit(1)
        args.oobe = True # Force OOBE bypass after flash

    if args.oobe or args.oobe_only:
        # --- Stage 0.5: ADB/USB Presence Check (Smart Multi-PID Check) ---
        logging.info("--- Stage 0.5: Monitoring for ADB or USB device (Timeout: 120s) ---")
        found_adb = False
        from hid_gadget.aoa_driver import AOA_VID, AOA_PID_ACC, AOA_PID_ACC_ADB, TRIMBLE_VID, TRIMBLE_PIDS, QUALCOMM_VID
        import usb.core
        import subprocess

        target_serial = args.serial
        usb_first_seen_time = None

        for attempt in range(120): # Total 120s timeout
            # 1. Quiet ADB Check
            try:
                adb_out = subprocess.check_output(["adb", "devices"]).decode()
                if target_serial:
                    if f"{target_serial}\tdevice" in adb_out:
                        found_adb = True
                        break
                else:
                    lines = [line for line in adb_out.splitlines() if "\tdevice" in line]
                    if lines:
                        target_serial = lines[0].split("\t")[0]
                        from framework import adb_helper
                        adb_helper.GLOBAL_SERIAL = target_serial
                        found_adb = True
                        logging.info(f"Stage 0.5: Auto-detected ADB device: {target_serial}")
                        break
            except: pass

            # 2. Quiet USB Scan
            all_devs = usb.core.find(find_all=True)
            found_usb_target = None
            for d in all_devs:
                is_known = False
                if d.idVendor == TRIMBLE_VID and d.idProduct in TRIMBLE_PIDS: is_known = True
                elif d.idVendor == QUALCOMM_VID and d.idProduct == 0x901d: is_known = True
                elif d.idVendor == AOA_VID and d.idProduct in [0x2d00, 0x2d01]: is_known = True

                if is_known:
                    try:
                        d_serial = d.serial_number
                        if not target_serial:
                            target_serial = d_serial
                            from framework import adb_helper
                            adb_helper.GLOBAL_SERIAL = target_serial
                            logging.info(f"Stage 0.5: Auto-locked onto USB device: {target_serial}")
                        
                        if d_serial == target_serial:
                            found_usb_target = d
                            break
                    except: continue

            if found_usb_target:
                # Case A: AOA mode -> Jump immediately
                if found_usb_target.idVendor == AOA_VID:
                    logging.info(f"Stage 0.5: Device {target_serial} already in AOA mode. Jumping to Stage 1.")
                    break
                
                # Case B: Qualcomm/Trimble Mode -> 15s timer from FIRST SIGHT
                if usb_first_seen_time is None:
                    usb_first_seen_time = time.time()
                    logging.info(f"Stage 0.5: USB device {target_serial} detected. Waiting 15s for ADB to wake up...")
                
                if time.time() - usb_first_seen_time > 15:
                    logging.info(f"Stage 0.5: 15s buffer reached for {target_serial} (No ADB). Proceeding to Stage 1.")
                    break
            
            if attempt % 10 == 0:
                logging.info(f"Stage 0.5: Searching for target device... ({attempt}s)")
            time.sleep(1)

        if found_adb:
            logging.info(f"Stage 0.5: ADB detected for {target_serial}!")
            boot_success = False
            for _ in range(30): # Max 60s
                _, boot_status = run_adb_cmd("getprop sys.boot_completed")
                if boot_status.strip() == "1":
                    boot_success = True
                    break
                time.sleep(2)
            
            if boot_success:
                logging.info("ADB detected, forcing bypass Setup Wizard and skipping HID ADB enablement.")
                run_adb_cmd("settings put global device_provisioned 1")
                run_adb_cmd("settings put secure user_setup_complete 1")
                run_adb_cmd("am start -c android.intent.category.HOME -a android.intent.action.MAIN")
                time.sleep(3)
            else:
                logging.warning("Wait for boot_completed timed out. Proceeding anyway.")
        else:
            # --- Stage 1: HID/AOA OOBE Bypass ---
            logging.info("--- Stage 1: HID/AOA OOBE Bypass (No ADB required) ---")
            from hid_gadget.oobe_bypass_script import run_oobe_bypass
            if not run_oobe_bypass(sku=args.sku, serial=target_serial, timeout=config.get('oobe_bypass_timeout', 300)):
                logging.error("OOBE Bypass failed or timed out.")
                sys.exit(1)

        if args.oobe_only or args.skip_tests:
            logging.info("OOBE/ADB Setup successful. Stopping as requested.")
            return

    # --- Phase 1: Environment Readiness ---
    # 3. Connection Pre-check
    logging.info("Checking for device availability...")
    if not wait_for_device(timeout=120):
        logging.error("Device connection timeout. Aborting tests.")
        sys.exit(1)

    # 4. Initialize UI Automation
    ui = UIHelper(serial=args.serial)
        
    # Pro-actively bypass Setup Wizard for newly flashed builds (via ADB as backup/second layer)
    if not args.only_tests:
        logging.info("Ensuring Setup Wizard is bypassed (ADB layer)...")
        # Wait for system stabilization before sending settings commands
        boot_ready = False
        for _ in range(30):
            _, boot_val = run_adb_cmd("getprop sys.boot_completed")
            if boot_val.strip() == "1":
                boot_ready = True
                break
            time.sleep(2)
            
        if boot_ready:
            run_adb_cmd("settings put global device_provisioned 1")
            run_adb_cmd("settings put secure user_setup_complete 1")
            if args.sku == "china":
                # 同步更新 Phase 1 邏輯，確保測試開始前已停用 China OOBE
                run_adb_cmd("pm disable com.pega.eulacn")
                run_adb_cmd("pm disable com.android.provision")
            run_adb_cmd("am start -c android.intent.category.HOME -a android.intent.action.MAIN")
            time.sleep(3)
        else:
            logging.warning("System not fully booted (boot_completed timeout), bypass may be incomplete.")

    if args.skip_tests:
        logging.info("Tests skipped as per --skip-tests flag.")
        return

    start_time = time.time()
        
    # Initialize Reporter
    reporter = HTMLReportGenerator(output_dir=args.report_dir)
    
    # [New] Inject profile content into report (with smart path resolution)
    try:
        profile_path = args.profile
        # Handle short names like 'stable_smoke'
        if not os.path.exists(profile_path) and not os.path.isabs(profile_path):
            alt_path = os.path.join("configs", "profiles", f"{args.profile}.yaml")
            if os.path.exists(alt_path):
                profile_path = alt_path
                
        with open(profile_path, 'r') as pf:
            profile_raw = pf.read()
            reporter.set_profile_content(profile_path, profile_raw)
    except Exception as e:
        logging.warning(f"Failed to read profile content for report: {e}")
    
    # Collect Device Info
    sku_raw = get_system_property("ro.boot.sku")
    build_type_raw = get_system_property("ro.build.type") # 自動偵測 user/userdebug
    
    # 智慧校正：如果偵測到的型態與參數不符，以機台實際型態為準
    if build_type_raw in ["user", "userdebug"]:
        args.type = build_type_raw

    # Load System Configurations from configs/
    
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
    reporter.set_tool_info({"version": VERSION})
    
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
        ui = UIHelper(serial=args.serial)
    except Exception as e:
        reporter.add_result("System", "UIAutomator Initialization", False, f"Failed to start uiautomator2 agent: {e}")
        reporter.finalize(time.time() - start_time, version=final_build_id, variant=args.type)
        sys.exit(1)
        
    reporter.add_result("System", "ADB & UIAutomator Connection", True, "Successfully connected to device and injected test agents.")
    
    # [New] China SKU Initial Popup Dismissal (For ADB-already-on devices)
    if args.sku == "china":
        logging.info("China SKU detected. Pre-emptively clearing Settings popups via UI...")
        try:
            ui.ensure_settings_ready()
        except Exception as e:
            logging.warning(f"Failed to clear China SKU popups: {e}")
    
    # Ensure screen is on and won't sleep during tests
    from framework.adb_helper import keep_screen_on, get_stay_on_state, set_stay_on_state
    
    # 1. Backup original state
    original_stay_on = get_stay_on_state()
    
    # 2. Force screen on and unlock
    keep_screen_on(True)

    # --- Environment Readiness & Security Preflight ---
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
            # 調整為非阻斷式：記錄警告但繼續執行
            msg_prefix = "WARNING" if args.type == "userdebug" else "SECURITY ALERT"
            logging.warning(f"{msg_prefix}: Insecure configuration detected on {args.type} build: {status_msg}")
            
            reporter.add_result("System", "Security Preflight", True, 
                                f"{msg_prefix}: {status_msg}", 
                                status_override="SKIP" if args.type == "userdebug" else "WARNING")
            
            if args.type == "user":
                logging.info("Proceeding with tests as requested, despite insecure environment.")
        else:
            reporter.add_result("System", "Security Preflight", True, f"Environment OK (SELinux: {selinux_status})")
            logging.info("Security Preflight Passed.")

        # --- Execute Test Modules ---
        logging.info("Executing configured test suites...")
        mods = config.get("modules", {})
        exclude_list = config.get("exclude_items", [])
        
        def should_run(mod_name):
            return mods.get(mod_name, True)
        
        # Helper to check if a specific test item should be skipped
        def is_excluded(item_name):
            return item_name in exclude_list
        
        # Initialize metric
        # Extract categorized specs from new config structure
        hw_specs = hw_specs_data.get("hardware", {})
        ui_selectors = ui_selectors_data.get("ui_selectors", {})
        fw_validations = build_info.get("validations", [])
        
        # Merge global config thresholds into hw_specs for dynamic override
        merged_specs = {**hw_specs, **config}
        
        # Priority: Reboot & Firmware
        if should_run("reboot"):
            test_reboot.run_tests(ui, reporter, timeout=config.get("reboot_timeout", 120))
        
        if should_run("firmware"):
            test_firmware.run_tests(ui, reporter, validations=fw_validations, excluded=exclude_list)
        
        # Phase 1
        if should_run("audio"):
            test_audio.run_tests(ui, reporter, specs=merged_specs, selectors=ui_selectors, excluded=exclude_list)
        if should_run("camera"):
            test_camera.run_tests(ui, reporter, specs=merged_specs, selectors=ui_selectors, excluded=exclude_list)
        if should_run("connectivity"):
            net_config = config.get("network", {})
            test_connectivity.run_tests(ui, reporter, 
                                        ssid=net_config.get("wifi_ssid"), 
                                        password=net_config.get("wifi_pass"),
                                        specs=merged_specs,
                                        selectors=ui_selectors,
                                        excluded=exclude_list)
        if should_run("sensors"):
            test_sensors.run_sensors_tests(ui, reporter, specs=merged_specs, excluded=exclude_list)
        if should_run("power"):
            test_sensors.run_power_tests(ui, reporter)
        if should_run("nfc"):
            test_nfc.run_tests(ui, reporter, excluded=exclude_list)
        if should_run("gps"):
            test_gps.run_tests(ui, reporter, excluded=exclude_list)

        # --- Final Metric Collection (Pre-Reset) ---
        if config.get('modules', {}).get('auto_factory_reset', False):
            # Create a marker file to ensure reset can be verified even if no tests ran
            logging.info("Creating reset marker file for verification...")
            run_adb_cmd("mkdir -p /sdcard/DCIM/Camera")
            run_adb_cmd("touch /sdcard/DCIM/Camera/reset_marker.txt")
            
            baseline_uptime, baseline_files = test_lifecycle.get_metrics()
            logging.info(f"Baseline captured: {baseline_files} files (includes marker), {baseline_uptime:.2f}h uptime")
    finally:
        # Restore original screen sleep settings after all tests finish
        logging.info("Tests finished. Restoring original device state...")
        if 'original_stay_on' in locals():
            set_stay_on_state(original_stay_on)
        else:
            # Fallback if backup failed
            keep_screen_on(False)
    
    # --- Phase 99: Final Lifecycle (Auto-Reset & Verify) ---
    if config.get('modules', {}).get('auto_factory_reset', False):
        logging.info("--- FULL CYCLE: Starting Automated Factory Reset & Verification ---")
        reset_success = False
        reset_error = ""
        
        try:
            from hid_gadget import oobe_bypass_script, aoa_driver, run_oobe_bypass
            
            # --- Robust Serial Recovery ---
            target_sn = args.serial
            if not target_sn:
                from framework import adb_helper
                target_sn = adb_helper.GLOBAL_SERIAL
                if not target_sn:
                    devices = adb_helper.list_adb_devices()
                    if devices:
                        target_sn = devices[0]
                        logging.info(f"Dynamically recovered target serial for reset: {target_sn}")
            
            driver = aoa_driver.AOADriver(serial=target_sn)
            
            # --- [New] ADB Fast Reset Strategy ---
            from framework.adb_helper import trigger_recovery_wipe
            adb_reset_success = False
            
            if trigger_recovery_wipe():
                logging.info("ADB Fast Reset initiated successfully.")
                adb_reset_success = True
            else:
                logging.warning("ADB Fast Reset failed or not supported. Falling back to HID sequence...")
                if driver.find_device(serial=target_sn):
                    if driver.switch_to_accessory_mode():
                        driver.register_hid(1, aoa_driver.KB_REPORT_DESC)
                        driver.register_hid(2, aoa_driver.CONSUMER_REPORT_DESC)
                        bypass = oobe_bypass_script.OOBEBypass(driver)
                        bypass.reset_device_to_factory_settings()
                    else:
                        reset_error = "Failed to switch to Accessory Mode for HID fallback"
                else:
                    reset_error = "HID Device not found for fallback"

            if adb_reset_success or not reset_error:
                # --- CRITICAL: Wait for device to actually disconnect and reboot ---
                logging.info("Waiting 20s for device to initiate factory reset and disconnect USB...")
                time.sleep(20)
                
                logging.info("Attempting OOBE Bypass & ADB Enablement after reset...")
                if run_oobe_bypass(sku=args.sku, serial=target_sn, timeout=config.get('oobe_bypass_timeout', 600)):
                    logging.info("Bypass successful. Waiting for ADB...")
                    if wait_for_device(timeout=60):
                        # Final Provisioning (Wait for system ready to ensure commands stick)
                        logging.info("Wait for system stabilization (sys.boot_completed) after reset...")
                        boot_ready = False
                        for _ in range(30):
                            _, boot_val = run_adb_cmd("getprop sys.boot_completed")
                            if boot_val.strip() == "1":
                                boot_ready = True
                                break
                            time.sleep(2)
                            
                        if boot_ready:
                            run_adb_cmd("settings put global device_provisioned 1")
                            run_adb_cmd("settings put secure user_setup_complete 1")
                            if args.sku == "china":
                                # 實測證明 China SKU 需停用此包名才能跳出 OOBE
                                run_adb_cmd("pm disable com.pega.eulacn")
                                run_adb_cmd("pm disable com.android.provision")
                            run_adb_cmd("am start -c android.intent.category.HOME -a android.intent.action.MAIN")
                            time.sleep(3)
                        else:
                            logging.warning("System not fully booted after reset, bypass might be incomplete.")
                        
                        # Final Metric Verification (Closure)
                        final_uptime, final_files = test_lifecycle.get_metrics()
                        
                        # Logic: Reset is successful if files are cleared (data wipe confirmed via marker deletion)
                        if final_files < baseline_files:
                            reset_success = True
                            status_msg = f"Full-cycle reset verified (Data Wiped). Files: {baseline_files} -> {final_files}, Uptime Ref: {final_uptime:.4f}h"
                        else:
                            reset_success = False
                            reset_error = f"Data not wiped. Files remained at {final_files}. Reset failed."
                    else:
                        reset_error = "ADB not authorized after reset"
                else:
                    reset_error = "OOBE Bypass failed or timed out"
        except Exception as e:
            reset_error = str(e)
            
        reporter.add_result("System", "Factory Reset Lifecycle", reset_success, 
                            status_msg if reset_success else f"Reset failed: {reset_error}")

    # Final summary log
    logging.info("Core test execution and lifecycle phases completed.")

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
    
    # --- Final Result Assessment (Industrial 3-Tier Logic) ---
    logging.info("--- Final Result Assessment (Industrial Logic) ---")
    
    # 1. Load Registry
    status_logic = {}
    logic_path = os.path.join("configs", "status_logic.yaml")
    if os.path.exists(logic_path):
        try:
            with open(logic_path, 'r') as f:
                logic_data = yaml.safe_load(f)
                # Convert list to dict for fast lookup
                for item in logic_data.get('items', []):
                    status_logic[item['name']] = item['level']
            logging.info(f"Loaded status logic registry with {len(status_logic)} items.")
        except Exception as e:
            logging.error(f"Failed to load status_logic.yaml: {e}")

    # 2. Classify Failures
    critical_fails = []
    partial_fails = []
    
    for res in reporter.results:
        if res["status"] in ["FAIL", "ERROR"]:
            name = res["test_name"]
            level = status_logic.get(name, "CRITICAL") # Default to CRITICAL if not found
            
            fail_info = f"{res['category']} > {name}"
            
            if level == "PARTIAL":
                partial_fails.append(fail_info)
            else:
                critical_fails.append(fail_info)

    # 3. Determine Overall Status & Exit Code
    final_status = "SUCCESS"
    exit_code = 0
    
    if critical_fails:
        final_status = "FAILED"
        exit_code = 1
    elif partial_fails:
        final_status = "PARTIAL"
        exit_code = 2
    
    # 4. Final Summary & Data Export
    logging.info(f"Assessment Summary: {final_status} (Exit: {exit_code})")
    logging.info(f" - Critical Failures: {len(critical_fails)}")
    logging.info(f" - Partial Failures: {len(partial_fails)}")
    
    # Export summary.json for CI orchestrators
    reporter.export_summary_json(version=final_build_id, variant=args.type, status=final_status)
    
    logging.info(f"--- Tests Completed in {duration:.1f}s ---")
    logging.info(f"Report location: {report_path}")
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
