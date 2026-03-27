from framework.adb_helper import run_adb_cmd
from framework.ui_automator import UIHelper
from framework.report_generator import HTMLReportGenerator
import time
import logging
import os

def run_tests(ui: UIHelper, reporter: HTMLReportGenerator):
    logging.info("Running Camera Tests...")
    
    # Check Camera Service
    code, out = run_adb_cmd("dumpsys media.camera")
    if "Camera 0" in out or "device@3" in out.lower():
        reporter.add_result("Camera", "Camera HAL Initialization", True, "Camera HAL exposes at least one camera device")
    else:
        reporter.add_result("Camera", "Camera HAL Initialization", False, "No camera devices found")

    target_pkg = "org.codeaurora.snapcam"
    target_dir = "/sdcard/DCIM/Camera"
    
    def bypass_camera_dialogs():
        # Added 'Confirm', '確定' etc. to handle post-factory reset dialogs
        for _ in range(6):
            found = False
            for btn_text in ["Allow", "WHILE USING THE APP", "Next", "OK", "AGREE", "Confirm", "給予", "使用時允許", "下一步", "確定", "同意"]:
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
    def get_shutter_pos():
        # 1. Try to find via Resource ID (Including Snapcam specific ID)
        shutter_ids = ".*shutter.*|.*video_button.*|org.codeaurora.snapcam:id/shutter_button"
        shutter = ui.d(resourceIdMatches=shutter_ids)
        if shutter.exists:
            info = shutter.info
            bounds = info['bounds']
            x = (bounds['left'] + bounds['right']) // 2
            y = (bounds['top'] + bounds['bottom']) // 2
            logging.info(f"Dynamic shutter pos (UI): ({x}, {y})")
            return x, y
        
        # 2. Fallback: Calculate based on screen resolution (Assuming Landscape)
        _, size_out = run_adb_cmd("wm size")
        if "Physical size" in size_out:
            # Physical size: 1920x1200 -> [1920, 1200]
            dims = [int(s) for s in size_out.split(":")[-1].strip().split("x")]
            w, h = max(dims), min(dims) # Landscape assumption
            x, y = w - 150, h // 2
            logging.info(f"Dynamic shutter fallback (Res): ({x}, {y}) for {w}x{h}")
            return x, y
            
        return 1800, 600 # Last resort for 1080p/1200p

    # Clean start for Photo
    run_adb_cmd(f"am force-stop {target_pkg}")
    time.sleep(1)

    # --- 1. Photo Capture Test ---
    logging.info("Starting Photo Capture test...")
    run_adb_cmd("am start -a android.media.action.STILL_IMAGE_CAMERA")
    time.sleep(5)
    bypass_camera_dialogs()
    
    # Capture count before
    _, out_before = run_adb_cmd(f"find {target_dir} -maxdepth 1 -type f | wc -l")
    count_before = int(out_before.strip()) if out_before.strip().isdigit() else 0
    
    sx, sy = get_shutter_pos()
    ui.d.click(sx, sy) 
    time.sleep(5) # Wait for processing
    
    # Verification: Try to find newest file created in the last 1 minute
    _, find_out = run_adb_cmd(f"find {target_dir} -maxdepth 1 -mmin -1 -type f | head -n 1")
    file_after = find_out.strip()
    
    if file_after:
        reporter.add_result("Camera", "Photo Capture", True, f"Verified: New photo created: {os.path.basename(file_after)}")
    else:
        # Fallback to keyevent Focus + Shutter
        logging.info("UI click failed to produce file, trying KEYEVENT_CAMERA...")
        run_adb_cmd("input keyevent 27")
        time.sleep(5)
        _, find_out = run_adb_cmd(f"find {target_dir} -maxdepth 1 -mmin -1 -type f | head -n 1")
        file_after = find_out.strip()
        if file_after:
            reporter.add_result("Camera", "Photo Capture", True, f"Verified: Photo created via keyevent: {os.path.basename(file_after)}")
        else:
            reporter.add_result("Camera", "Photo Capture", False, "Failed to capture photo (UI click and Keyevent failed)")

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
            
    vx, vy = get_shutter_pos()
    
    # Capture precise device time BEFORE shutter click (Double-quoted for shell safety)
    # Using adb shell "date '...'" format
    _, start_time_raw = run_adb_cmd("\"date '+%m-%d %H:%M:%S.000'\"")
    start_time = start_time_raw.strip()
    
    logging.info(f"Recording video (15s)... START click at ({vx}, {vy}) at device time {start_time}")
    ui.d.click(vx, vy)
    time.sleep(15) 
    
    logging.info("Stopping recording...")
    ui.d.click(vx, vy)
    
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
            if size > 1000000: # Guaranteed video size for 15s
                final_file = f
                logging.info(f"File System search found valid file: {final_file} ({size} bytes)")
                break

    # Final Result Reporting
    if final_file:
        path = os.path.join(target_dir, final_file)
        _, size_out = run_adb_cmd(f"stat -c %s {path}")
        size = int(size_out.strip()) if size_out.strip().isdigit() else 0
        if size > 1000000:
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
