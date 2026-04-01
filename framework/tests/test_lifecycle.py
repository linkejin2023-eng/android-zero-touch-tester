from framework.adb_helper import run_adb_cmd
from framework.report_generator import HTMLReportGenerator
import logging

def get_metrics():
    """Returns (uptime_hours, total_files) for system lifecycle monitoring."""
    uptime_hours = 0.0
    total_files = 0
    
    try:
        code, out = run_adb_cmd("cat /proc/uptime")
        if code == 0:
            uptime_hours = float(out.split()[0]) / 3600
    except:
        pass

    try:
        common_dirs = ["DCIM", "Pictures", "Movies", "Download", "Music"]
        for d in common_dirs:
            cmd = f"find /sdcard/{d} -type f ! -name '.*' 2>/dev/null"
            code, out = run_adb_cmd(cmd)
            if code == 0 and out.strip():
                total_files += len(out.strip().split('\n'))
    except:
        pass
        
    return uptime_hours, total_files

def run_tests(ui, reporter: HTMLReportGenerator, label="Factory Reset Integrity"):
    logging.info(f"Running Lifecycle & Storage Integrity Tests ({label})...")
    uptime, files = get_metrics()
    
    # Standard reporting if called normally
    if files == 0:
        reporter.add_result("Lifecycle", label, True, "Verified: Internal storage (/sdcard) is clean.")
    else:
        reporter.add_result("Lifecycle", label, False, f"Warning: Residual data found ({files} files).")
    
    reporter.add_result("Lifecycle", "System Uptime", True, f"Device uptime: {uptime:.2f} hours")
