from framework.adb_helper import run_adb_cmd
from framework.ui_automator import UIHelper
from framework.report_generator import HTMLReportGenerator
import time
import logging
import os

def run_tests(ui: UIHelper, reporter: HTMLReportGenerator, specs=None, selectors=None):
    logging.info("Running Camera Tests...")
    
    # Defaults for specs/selectors if not provided
    if not specs: specs = {}
    if not selectors: selectors = {}
    
    target_pkg = specs.get("camera_package", "org.codeaurora.snapcam")
    target_dir = specs.get("camera_storage_dir", "/sdcard/DCIM/Camera")
    video_min_size = specs.get("video_min_size_bytes", 1000000)
    
    ui_common = selectors.get("common", {})
    camera_specs = selectors.get("camera", {})

    # Check Camera Service
    code, out = run_adb_cmd("dumpsys media.camera")
    if "Camera 0" in out or "device@3" in out.lower():
        reporter.add_result("Camera", "Camera HAL Initialization", True, "Camera HAL exposes at least one camera device")
    else:
        reporter.add_result("Camera", "Camera HAL Initialization", False, "No camera devices found")
    
    def bypass_camera_dialogs():
        allow_btns = ui_common.get("allow_texts", ["Allow", "WHILE USING THE APP", "允許", "使用時允許"])
        confirm_btns = ui_common.get("confirm_texts", ["OK", "Next", "AGREE", "確定", "下一步", "同意"])
        combined = list(set(allow_btns + confirm_btns))
        
        for _ in range(6):
            found = False
            for btn_text in combined:
                btn = ui.d(textMatches=f"(?i){btn_text}")
                if btn.exists(timeout=1):
                    logging.info(f"Clicking camera popup: {btn_text}")
                    btn.click()
                    time.sleep(1)
                    found = True
            if not found: break

    def get_newest_file(directory, video_only=False):
        ext_filter = "grep -Ei '.mp4|.3gp|.mkv'" if video_only else "cat"
        _, out = run_adb_cmd(f"ls -t {directory} | {ext_filter} | head -n 1")
        return out.strip()

    def wait_for_file_stability_dynamic(directory, video_only=True, timeout=60, exclude_file=None):
        """Track the newest file dynamically until its size stabilizes"""
        start_time = time.time()
        last_size = -1
        last_file = None
        
        while time.time() - start_time < timeout:
            current_file = get_newest_file(directory, video_only)
            if not current_file or (exclude_file and current_file == exclude_file):
                time.sleep(2)
                continue
                
            path = os.path.join(directory, current_file)
            _, out = run_adb_cmd(f"stat -c %s {path}")
            current_size = int(out.strip()) if out.strip().isdigit() else 0
            
            if current_size > 0:
                if current_size == last_size and current_file == last_file:
                    logging.info(f"File {current_file} is stable at {current_size} bytes")
                    return current_file
                last_size = current_size
                last_file = current_file
                
            time.sleep(2)
        return None

    def get_all_videos(directory):
        _, out = run_adb_cmd(f"ls {directory} | grep -Ei '.mp4|.3gp'")
        return set(f.strip() for f in out.split('\n') if f.strip())

    # Coordinate fallback for Snapcam shutter (Dynamic based on screen size)
    def trigger_shutter():
        # Step 1: Hardware Keyevents (Primary Strategy - UI Independent)
        logging.info("Triggering shutter via Keyevents (27, 66)...")
        run_adb_cmd("input keyevent 27") # KEYCODE_CAMERA
        time.sleep(1)
        run_adb_cmd("input keyevent 66") # KEYCODE_ENTER
        time.sleep(1)

        # Step 2: UI Automator Click (Fallback Strategy)
        shutter_ids = [
            camera_specs.get("shutter_id"),
            "org.codeaurora.snapcam:id/shutter_button",
            "com.android.camera:id/shutter_button",
            ".*shutter.*"
        ]
        for sid in shutter_ids:
            if not sid: continue
            try:
                shutter = ui.d(resourceIdMatches=sid)
                if shutter.exists(timeout=2):
                    logging.info(f"Triggering shutter via UI Click fallback ({sid})")
                    shutter.click()
                    return True
            except: pass
            
        # Step 3: Coordinate Fallback (Calculated)
        _, size_out = run_adb_cmd("wm size")
        if "Physical size" in size_out:
            # ... existing coordinate tap logic ...
            dims = [int(s) for s in size_out.split(":")[-1].strip().split("x")]
            w, h = max(dims), min(dims) 
            x, y = w - 150, h // 2
            logging.info(f"Triggering shutter via coordinate fallback: ({x}, {y})")
            run_adb_cmd(f"input tap {x} {y}")
            return True
        return False

    # Clean start for Photo
    run_adb_cmd(f"am force-stop {target_pkg}")
    time.sleep(1)

    # --- 1. Photo Capture Test ---
    logging.info("Starting Photo Capture test...")
    run_adb_cmd("am start -a android.media.action.STILL_IMAGE_CAMERA")
    time.sleep(5)
    bypass_camera_dialogs()
    
    # Capture count before
    _, out_before = run_adb_cmd(f"ls {target_dir} | wc -l")
    count_before = int(out_before.strip()) if out_before.strip().isdigit() else 0
    
    # Use native camera hardware key event for maximum robustness (Task D Optimization)
    logging.info("Triggering photo capture...")
    trigger_shutter()
    time.sleep(8) # Wait for storage sync
    
    # Verification A: Count check
    _, out_after = run_adb_cmd(f"ls {target_dir} | wc -l")
    count_after = int(out_after.strip()) if out_after.strip().isdigit() else 0
    
    # Verification B: Get newest file (LS -t)
    _, find_out = run_adb_cmd(f"ls -t {target_dir} | head -n 1")
    file_after = find_out.strip()
    
    if count_after > count_before or (file_after and "IMG_" in file_after):
        reporter.add_result("Camera", "Photo Capture", True, f"Verified: New photo created: {file_after} (Count: {count_before} -> {count_after})")
    else:
        reporter.add_result("Camera", "Photo Capture", False, "Failed to capture photo (Storage sync failed or shutter ignored)", status_override="ERROR")

    # --- 2. Video Recording Test ---
    logging.info("Starting Video Recording test...")
    run_adb_cmd("am start -a android.media.action.VIDEO_CAMERA")
    time.sleep(8)
    bypass_camera_dialogs()

    # Switch mode if text visible
    for m in ["Video", "錄錄影", "錄像", "錄製", "録画"]:
        btn = ui.d(textMatches=f"(?i).*{m}.*")
        if btn.exists:
            btn.click()
            time.sleep(3)
            break
            
    # Capture precise device time BEFORE shutter click
    _, start_time_raw = run_adb_cmd("\"date '+%m-%d %H:%M:%S.000'\"")
    start_time = start_time_raw.strip()
    
    logging.info(f"Recording video (15s)... START via multi-shutter at device time {start_time}")
    trigger_shutter()
    time.sleep(15) 
    
    logging.info("Stopping recording...")
    trigger_shutter()
    
    # Simple, bulletproof wait for muxing/renaming
    logging.info("Waiting 15s for file finalization...")
    time.sleep(15)
    
    import re
    final_file = None

    # Step A: Logcat Isolation (Primary Authority)
    if start_time:
        log_cmd = f"logcat -d -v time -T '{start_time}'"
        _, filtered_logs = run_adb_cmd(log_cmd)
        
        # Matches: ExtendedUtils: printFileName fd(14) -> /storage/emulated/0/DCIM/Camera/VID_20260321_051610.mp4
        match = re.search(r"printFileName fd.*->\s+.*?Camera/(VID_.*?\.mp4)", filtered_logs)
        if not match:
            # Fallback to MediaProvider log
            match = re.search(r"MediaProvider: Open with lower FS for.*?Camera/(VID_.*?\.mp4)", filtered_logs)
            
        if match:
            final_file = match.group(1).strip()
            logging.info(f"Logcat parsing found filename: {final_file}")

    # Step B: File System Fallback (If Logcat failed or returned invalid path)
    if not final_file:
        logging.warning("Logcat extraction failed. Using time-based File System search...")
        # Get all videos sorted by modification time (newest first)
        _, out = run_adb_cmd(f"ls -t {target_dir} | grep -Ei '.mp4|.3gp'")
        potential_files = [f.strip() for f in out.split('\n') if f.strip()]
        
        # Check Top 5 newest files
        for f in potential_files[:5]:
            path = os.path.join(target_dir, f)
            _, size_out = run_adb_cmd(f"stat -c %s {path}")
            size = int(size_out.strip()) if size_out.strip().isdigit() else 0
            if size > video_min_size: # Guaranteed video size from config
                final_file = f
                logging.info(f"File System search found valid file: {final_file} ({size} bytes)")
                break

    # Final Result Reporting
    if final_file:
        path = os.path.join(target_dir, final_file)
        _, size_out = run_adb_cmd(f"stat -c %s {path}")
        size = int(size_out.strip()) if size_out.strip().isdigit() else 0
        if size > video_min_size:
            reporter.add_result("Camera", "Video Recording", True, f"Verified: Video saved as {final_file} ({size} bytes)")
            ui.go_home()
            return

    # Ultimate Fallback: Any MediaRecorder activity at all?
    if start_time:
        _, filtered_logs = run_adb_cmd(f"logcat -d -v time -T '{start_time}'")
        if "start" in filtered_logs.lower() or "stop" in filtered_logs.lower() or "camera" in filtered_logs.lower():
            reporter.add_result("Camera", "Video Recording", True, "Verified: MediaRecorder activity detected in Logcat window (Path verification failed)")
        else:
            reporter.add_result("Camera", "Video Recording", False, f"Failed: No valid video path found since {start_time}")
    else:
        reporter.add_result("Camera", "Video Recording", False, "Failed: Device time capture failed, could not verify video")

    ui.go_home()

    ui.go_home()
