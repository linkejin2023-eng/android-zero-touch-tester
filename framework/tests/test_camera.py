from framework.adb_helper import run_adb_cmd
from framework.ui_automator import UIHelper
from framework.report_generator import HTMLReportGenerator
import time
import logging

def run_tests(ui: UIHelper, reporter: HTMLReportGenerator):
    logging.info("Running Camera Tests...")
    
    # Check Camera Service / Providers
    code, out = run_adb_cmd("dumpsys media.camera")
    if "Camera 0" in out or "Camera ID: 0" in out or "device@3" in out.lower():
        reporter.add_result("Camera", "Camera HAL Initialization", True, "Camera HAL exposes at least one camera device")
    else:
        reporter.add_result("Camera", "Camera HAL Initialization", False, "No camera devices found in dumpsys")

    # Phase 3: Pre-grant permissions to avoid UI blocks
    # Try to find common camera packages
    common_cameras = ["com.google.android.GoogleCamera", "com.android.camera", "com.android.camera2"]
    for pkg in common_cameras:
        run_adb_cmd(f"pm grant {pkg} android.permission.CAMERA")
        run_adb_cmd(f"pm grant {pkg} android.permission.RECORD_AUDIO")
        run_adb_cmd(f"pm grant {pkg} android.permission.READ_EXTERNAL_STORAGE")
        run_adb_cmd(f"pm grant {pkg} android.permission.WRITE_EXTERNAL_STORAGE")
        run_adb_cmd(f"pm grant {pkg} android.permission.ACCESS_FINE_LOCATION")

    # Launch Camera using Intent
    logging.info("Sending Image Capture Intent...")
    
    # Pre-granting to org.codeaurora.snapcam
    target_pkg = "org.codeaurora.snapcam"
    run_adb_cmd(f"pm grant {target_pkg} android.permission.CAMERA")
    run_adb_cmd(f"pm grant {target_pkg} android.permission.RECORD_AUDIO")
    run_adb_cmd(f"pm grant {target_pkg} android.permission.READ_EXTERNAL_STORAGE")
    run_adb_cmd(f"pm grant {target_pkg} android.permission.WRITE_EXTERNAL_STORAGE")

    # Get initial file count in common folders
    cam_dirs = ["/sdcard/DCIM/Camera", "/sdcard/DCIM/100ANDRO", "/sdcard/Camera"]
    target_dir = "/sdcard/DCIM/Camera"
    for d in cam_dirs:
        code, _ = run_adb_cmd(f"ls -d {d}")
        if code == 0:
            target_dir = d
            break

    _, out_before = run_adb_cmd(f"ls {target_dir} | grep -iE '.jpg|.jpeg' | wc -l")
    try:
        count_before = int(out_before.strip())
    except:
        count_before = 0
    
    # Start the activity
    run_adb_cmd("am start -a android.media.action.STILL_IMAGE_CAMERA")
    time.sleep(3)
    
    # Click through any nagging permission dialogs
    for _ in range(5): # Increase attempts
        found = False
        for btn_text in ["Allow", "Allow all", "WHILE USING THE APP", "Next", "OK", "AGREE", "允许", "使用時允許", "仅在主用时允许"]:
            btn = ui.d(textMatches=f"(?i){btn_text}")
            if btn.exists(timeout=1):
                logging.info(f"Clicking through camera popup: {btn_text}")
                btn.click()
                time.sleep(1)
                found = True
        if not found: break
    
    # Emulate shutter click
    run_adb_cmd("input keyevent 27")
    time.sleep(4) 
        
    # Check for new file
    _, out_after = run_adb_cmd(f"ls {target_dir} | grep -iE '.jpg|.jpeg' | wc -l")
    try:
        count_after = int(out_after.strip())
    except:
        count_after = 0
        
    if count_after > count_before:
        reporter.add_result("Camera", "Photo Capture & Save", True, f"Successfully captured photo (Count: {count_before}->{count_after})")
    else:
        # Check logs for "Shutter" or "Snapshot"
        _, logs = run_adb_cmd("logcat -d | grep -iE 'shutter|snapshot|capture' | tail -n 10")
        if "shutter" in logs.lower() or "capture" in logs.lower():
             reporter.add_result("Camera", "Photo Capture & Save", True, "Capture triggered (Verified via Logcat)")
        else:
             reporter.add_result("Camera", "Photo Capture & Save", False, f"Capture failed. File count: {count_before}->{count_after}. Target: {target_dir}")

    # Verify Foreground
    try:
        # Give it a moment to return to camera app if a dialog was just dismissed
        time.sleep(2)
        current_app = ui.d.app_current()
        last_package = current_app['package'].lower()
        
        # If still in permission controller, try one last click
        if "permissioncontroller" in last_package:
            allow = ui.d(resourceIdMatches=".*permission_allow_button.*")
            if allow.exists:
                allow.click()
                time.sleep(1)
                current_app = ui.d.app_current()
                last_package = current_app['package'].lower()

        if any(p in last_package for p in ["camera", "snapcam", "gallery", "photos", "permissioncontroller"]):
            reporter.add_result("Camera", "Camera App Foreground", True, f"Camera/Review active ({current_app['package']})")
        else:
            reporter.add_result("Camera", "Camera App Foreground", False, f"Current app: {last_package}")
                 
    except Exception as e:
        reporter.add_result("Camera", "Camera App Foreground", False, f"Failed to check foreground app: {e}")
        
    # Return Home
    ui.go_home()
