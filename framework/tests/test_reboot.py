from framework.adb_helper import run_adb_cmd, wait_for_device
from framework.ui_automator import UIHelper
from framework.report_generator import HTMLReportGenerator
import time
import logging

def run_tests(ui: UIHelper, reporter: HTMLReportGenerator):
    logging.info("--- Starting Reboot Stability Test ---")
    
    start_time = time.time()
    
    # 1. Trigger Reboot
    logging.info("Triggering 'adb reboot'...")
    run_adb_cmd("reboot")
    
    # 2. Wait for disconnect
    logging.info("Waiting for device to disconnect...")
    time.sleep(5)
    
    # 3. Wait for reconnect
    logging.info("Waiting for device to reconnect via ADB...")
    if not wait_for_device(timeout=120):
        reporter.add_result("System", "Reboot Test", False, "Failed: Device did not return to ADB within 120s")
        return

    # 4. Wait for boot completion
    logging.info("Waiting for 'sys.boot_completed'...")
    boot_done = False
    for _ in range(60): # Max 60s more
        _, out = run_adb_cmd("getprop sys.boot_completed")
        if out.strip() == "1":
            boot_done = True
            break
        time.sleep(2)
        
    if not boot_done:
        reporter.add_result("System", "Reboot Test", False, "Failed: Boot signaled incomplete (sys.boot_completed != 1)")
        return

    # 5. Measure Boot Time
    end_time = time.time()
    boot_duration = end_time - start_time
    
    # Also get kernel uptime as cross-reference
    _, uptime_out = run_adb_cmd("cat /proc/uptime")
    uptime_sec = uptime_out.split()[0] if uptime_out else "Unknown"

    reporter.add_result("System", "Reboot Stability", True, f"Device successfully rebooted. Total time taken: {boot_duration:.1f}s (Kernel uptime: {uptime_sec}s)")
    logging.info(f"Reboot test passed in {boot_duration:.1f}s")
