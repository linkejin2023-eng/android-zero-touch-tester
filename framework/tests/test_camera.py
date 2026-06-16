from framework.adb_helper import run_adb_cmd
from framework.ui_automator import UIHelper
from framework.report_generator import HTMLReportGenerator
import time
import logging
import os

def run_tests(ui: UIHelper, reporter: HTMLReportGenerator, specs=None, selectors=None, excluded=None):
    if not excluded: excluded = []
    logging.info("Running Camera Tests...")
    
    # Defaults for specs/selectors if not provided
    if not specs: specs = {}
    if not selectors: selectors = {}
    
    target_pkg = specs.get("camera_package", "org.codeaurora.snapcam")
    target_dir = specs.get("camera_storage_dir", "/sdcard/DCIM/Camera")
    video_min_size = specs.get("video_min_size_bytes", 1000000)
    stability_timeout = specs.get("camera_file_timeout", 60)
    
    ui_common = selectors.get("common", {})
    camera_specs = selectors.get("camera", {})

    # Check Camera Service
    if "Camera HAL Initialization" not in excluded:
        code, out = run_adb_cmd("dumpsys media.camera")
        if "Camera 0" in out or "device@3" in out.lower():
            reporter.add_result("Camera", "Camera HAL Initialization", True, "Camera HAL exposes at least one camera device")
        else:
            reporter.add_result("Camera", "Camera HAL Initialization", False, "No camera devices found")
    else:
        reporter.add_result("Camera", "Camera HAL Initialization", True, "Skipped by profile", status_override="SKIP")
    
    def bypass_camera_dialogs():
        # Proactively tap the bottom-right region (approx 78% width, 70% height) to dismiss tutorial overlay
        _, size_out = run_adb_cmd("wm size")
        if "Physical size" in size_out:
            dims = [int(s) for s in size_out.split(":")[-1].strip().split("x")]
            w, h = max(dims), min(dims)
            tx, ty = int(w * 0.78), int(h * 0.7)
            logging.info(f"Proactively tapping tutorial overlay OK button at ({tx}, {ty}) for {w}x{h}")
            run_adb_cmd(f"input tap {tx} {ty}")
            time.sleep(1.5)

        allow_btns = ui_common.get("allow_texts", ["Allow", "WHILE USING THE APP", "允許", "使用時允許", "使用时允许", "仅限一次", "仅限这一次", "永远允许", "始终允许", "始终", "仅在使用该应用时允许", "仅本次使用时允许"])
        confirm_btns = ui_common.get("confirm_texts", ["OK", "Next", "AGREE", "確定", "下一步", "同意", "允许", "同意并继续", "确认", "确定"])
        combined = list(set(allow_btns + confirm_btns))
        pattern = "|".join(f".*{btn}.*" for btn in combined)
        
        for _ in range(3):
            try:
                # Add clickable=True to prevent matching unclickable dialog titles (e.g. "Allow Camera to...")
                btn = ui.d(textMatches=f"(?i)({pattern})", clickable=True)
                if btn.exists(timeout=0.5):
                    btn_text = btn.info.get('text', 'unknown')
                    logging.info(f"Clicking camera popup: {btn_text}")
                    btn.click(timeout=1)
                    time.sleep(1)
                else:
                    break
            except Exception as e:
                logging.warning(f"Error in bypass_camera_dialogs: {e}")
                break

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

    def get_all_media(directory, pattern):
        _, out = run_adb_cmd(f"ls {directory} | grep -Ei '{pattern}'")
        return set(f.strip() for f in out.split('\n') if f.strip())

    # Proportional coordinate calculation for shutter based on screen size (landscape 93% width, 50% height)
    def trigger_shutter(is_video=False):
        force_ui = camera_specs.get("force_ui_shutter", False)
        
        # Helper to do dynamic coordinate tap (proportional calculation)
        def do_coordinate_tap():
            _, size_out = run_adb_cmd("wm size")
            if "Physical size" in size_out:
                dims = [int(s) for s in size_out.split(":")[-1].strip().split("x")]
                w, h = max(dims), min(dims) 
                # Shutter button centers around 93% of the horizontal screen length in landscape mode
                x, y = int(w * 0.93), h // 2
                logging.info(f"Triggering shutter via proportional coordinate fallback: ({x}, {y}) for {w}x{h}")
                run_adb_cmd(f"input tap {x} {y}")
                return True
            return False

        if not force_ui and not is_video:
            # Step 1: Hardware Keyevents (Primary Strategy for Photo - UI Independent)
            logging.info("Triggering shutter via Keyevents (27)...")
            run_adb_cmd("input keyevent 27") # KEYCODE_CAMERA
            time.sleep(1)
            # DO NOT return True here. Let it also try the UI click as a fallback,
            # because on GMS SKU, KEYCODE_CAMERA is often ignored by Snapcam.

        # Step 2: UI Automator Click (Primary for Video, Fallback for Photo)

        # Step 2: UI Automator Click (Fallback Strategy for Photo)
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
                    # Use click() for photo, but for video we want a fast tap to avoid blocking
                    bounds = shutter.info['bounds']
                    cx = (bounds['left'] + bounds['right']) // 2
                    cy = (bounds['top'] + bounds['bottom']) // 2
                    run_adb_cmd(f"input tap {cx} {cy}")
                    return True
            except: pass
            
        # Step 3: Coordinate Fallback (Calculated)
        return do_coordinate_tap()

    # Clean start for Photo
    run_adb_cmd(f"am force-stop {target_pkg}")
    time.sleep(1)

    # --- 1. Photo Capture Test ---
    if "Photo Capture" not in excluded:
        logging.info("Starting Photo Capture test...")
        run_adb_cmd("am start -a android.media.action.STILL_IMAGE_CAMERA")
        time.sleep(5)
        bypass_camera_dialogs()
        
        # Capture media list before
        photos_before = get_all_media(target_dir, '.jpg|.png|.jpeg')
        
        # Use native camera hardware key event for maximum robustness (Task D Optimization)
        logging.info("Triggering photo capture...")
        trigger_shutter()
        time.sleep(8) # Wait for storage sync
        
        # Capture media list after
        photos_after = get_all_media(target_dir, '.jpg|.png|.jpeg')
        new_photos = list(photos_after - photos_before)
        
        if new_photos:
            reporter.add_result("Camera", "Photo Capture", True, f"Verified: New photo created: {new_photos[0]} (Count: {len(photos_before)} -> {len(photos_after)})")
        else:
            reporter.add_result("Camera", "Photo Capture", False, "Failed to capture photo (Storage sync failed or shutter ignored)", status_override="ERROR")
    else:
        reporter.add_result("Camera", "Photo Capture", True, "Skipped by profile", status_override="SKIP")

    # --- 2. Video Recording Test ---
    if "Video Recording" not in excluded:
        logging.info("Starting Video Recording test...")
        # Get videos before recording (CRITICAL: query before camera launch/force-stop to correctly include auto-record files!)
        videos_before = get_all_media(target_dir, '.mp4|.3gp')

        # Force stop the camera before starting Video test to avoid stream/buffer lock (Scheme B)
        run_adb_cmd(f"am force-stop {target_pkg}")
        time.sleep(1)
        run_adb_cmd("am start -a android.media.action.VIDEO_CAMERA")
        time.sleep(6) # Give plenty of time for fresh launch
        bypass_camera_dialogs()

        # Switch mode if text visible (Use ADB tap instead of UI click for reliability)
        mode_switched = False
        for m in ["Video", "錄錄影", "錄像", "錄製", "録画", "视频"]:
            try:
                btn = ui.d(textMatches=f"(?i).*{m}.*")
                if btn.exists(timeout=2):
                    bounds = btn.info['bounds']
                    cx = (bounds['left'] + bounds['right']) // 2
                    cy = (bounds['top'] + bounds['bottom']) // 2
                    logging.info(f"Switching to Video mode via tap at ({cx}, {cy}) for '{m}'")
                    run_adb_cmd(f"input tap {cx} {cy}")
                    time.sleep(3)
                    mode_switched = True
                    break
            except Exception as e:
                logging.warning(f"Mode switch tap failed: {e}")
                
        # Fallback: If UI text switch failed (e.g. unknown language), use T70 landscape proportional coordinates (w * 0.35, h * 0.84)
        if not mode_switched:
            try:
                w, h = ui.d.window_size()
                cx = int(w * 0.35)
                cy = int(h * 0.84)
                logging.info(f"UI mode text not matched (possibly unsupported language). Using proportional coordinate fallback tap at ({cx}, {cy}) for {w}x{h}")
                run_adb_cmd(f"input tap {cx} {cy}")
                time.sleep(3)
            except Exception as e:
                logging.warning(f"Proportional mode switch fallback failed: {e}")
                
        # Capture precise device time BEFORE shutter click
        _, start_time_raw = run_adb_cmd("\"date '+%m-%d %H:%M:%S.000'\"")
        start_time = start_time_raw.strip()
        
        logging.info(f"Recording video (15s)... START via multi-shutter at device time {start_time}")
        trigger_shutter(is_video=True)
        time.sleep(15) 
        
        logging.info("Stopping recording...")
        trigger_shutter(is_video=True)
        time.sleep(3) # Give camera 3s to gracefully stop recording thread
        
        # Force stop the camera app to trigger Snapcam's file finalization and renaming immediately
        logging.info("Stopping camera app to force file finalization and renaming...")
        run_adb_cmd(f"am force-stop {target_pkg}")
        time.sleep(2)
        
        # Get videos after recording
        videos_after = get_all_media(target_dir, '.mp4|.3gp')
        new_videos = list(videos_after - videos_before)
        
        # Select the largest video file among new videos to filter out 0-byte temp/spurious files
        final_file = None
        max_size = -1
        for f in new_videos:
            f_path = os.path.join(target_dir, f)
            _, size_out = run_adb_cmd(f"stat -c %s '{f_path}'")
            f_size = int(size_out.strip()) if size_out.strip().isdigit() else 0
            if f_size > max_size:
                max_size = f_size
                final_file = f

        # Final Result Reporting
        if final_file:
            if max_size > video_min_size:
                reporter.add_result("Camera", "Video Recording", True, f"Verified: Video saved as {final_file} ({max_size} bytes)")
            else:
                 reporter.add_result("Camera", "Video Recording", False, f"Video file found but too small ({max_size} bytes)")
        else:
            reporter.add_result("Camera", "Video Recording", False, "Failed: No new video file found via Set Difference")
    else:
        reporter.add_result("Camera", "Video Recording", True, "Skipped by profile", status_override="SKIP")

    ui.go_home()

    ui.go_home()
    ui.go_home()
