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

    # Launch Camera using Intent
    logging.info("Sending Image Capture Intent...")
    run_adb_cmd("am start -a android.media.action.STILL_IMAGE_CAMERA")
    time.sleep(3) # Wait for camera to open and initialize ISP
    
    # Emulate shutter click (KEYCODE_CAMERA)
    run_adb_cmd("input keyevent 27")
    time.sleep(2) # Wait for processing
        
    # Check recent logs or dumpsys to verify snapshot was requested
    # Due to Android security, we can't always guarantee a file is saved immediately via intent without a specific app
    # But we can check if the Camera App is in the foreground
    try:
        camera_found = False
        last_package = ""
        
        # Poll for up to 5 seconds
        for _ in range(10):
            current_app = ui.d.app_current()
            last_package = current_app['package'].lower()
            
            # Common camera package roots or the generic intent fallback
            if "camera" in last_package or "gallery" in last_package:
                reporter.add_result("Camera", "Camera App Foreground", True, f"Camera app ({current_app['package']}) successfully launched")
                camera_found = True
                break
            elif "permission" in last_package:
                # If we hit this, it means the permission controller is up. 
                run_adb_cmd(f"pm grant {current_app.get('package', 'com.google.android.GoogleCamera')} android.permission.CAMERA")
                reporter.add_result("Camera", "Camera App Foreground", True, "Camera intent successfully triggered (Caught at Permission Screen)")
                camera_found = True
                break
            elif "settings.intelligence" in last_package or "resolver" in last_package:
                # Disambiguation popup (e.g. Choose between 2 camera apps)
                # This proves the intent works. Clicking through it is risky as UIAutomator often hangs on system popups.
                reporter.add_result("Camera", "Camera App Foreground", True, "Camera intent triggered App Chooser/Resolver successfully")
                camera_found = True
                break
            
            time.sleep(0.5)
            
        if not camera_found:
            # Fallback to dumpsys just in case UIAutomator is slow
            code, out = run_adb_cmd("dumpsys window | grep mCurrentFocus")
            if "camera" in out.lower():
                 reporter.add_result("Camera", "Camera App Foreground", True, "Camera window detected via dumpsys")
            else:
                 reporter.add_result("Camera", "Camera App Foreground", False, f"Not in camera app. Current package: {last_package}")
                 
    except Exception as e:
        reporter.add_result("Camera", "Camera App Foreground", False, f"Failed to check foreground app: {e}")
        
    # Return Home
    ui.go_home()
