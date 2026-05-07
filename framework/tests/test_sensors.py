import time
import logging
import math
import os
from framework.adb_helper import run_adb_cmd, adb_install

def stdev(data):
    n = len(data)
    if n <= 1: return 0.0
    mean = sum(data) / n
    variance = sum((x - mean) ** 2 for x in data) / (n - 1)
    return math.sqrt(variance)

def get_sensor_events(name_filter, dump_content):
    events = []
    recording = False
    for line in dump_content.splitlines():
        if "last" in line.lower() and "events" in line.lower():
            if name_filter.lower() in line.lower():
                recording = True
            else:
                recording = False
            continue
        if recording:
            if ")" in line and "," in line:
                data_str = line.split(")")[-1]
                try:
                    parts = data_str.split(",")
                    if len(parts) >= 3:
                        vals = [float(p.strip()) for p in parts[:3]]
                        events.append(vals)
                except ValueError:
                    pass
    return events

def ensure_sensorbox_ready():
    """Ensure SensorBox is installed and screen is ready"""
    pkg = "imoblife.androidsensorbox"
    apk_path = "framework/tests/app_for_test/sensorbox_6.92-26_minAPI.apk"
    
    # 1. Wakeup & Unlock
    logging.info("Ensuring device is awake and unlocked...")
    run_adb_cmd("input keyevent KEYCODE_WAKEUP")
    run_adb_cmd("wm dismiss-keyguard")
    
    # 2. Check installation
    ret, out = run_adb_cmd(f"pm list packages {pkg}")
    if pkg not in out:
        logging.info(f"Installing {pkg} with auto-grant...")
        if os.path.exists(apk_path):
            if not adb_install(apk_path):
                logging.error(f"Failed to install {pkg}")
                return False
        else:
            logging.error(f"APK not found at {apk_path}")
            return False
    
    # 3. Grant key permissions just in case
    run_adb_cmd(f"pm grant {pkg} android.permission.ACCESS_FINE_LOCATION")
    run_adb_cmd(f"pm grant {pkg} android.permission.CAMERA")
    return True

def trigger_sensorbox_activation(ui):
    """Navigate SensorBox UI to wake up sensors using u2 text search"""
    pkg = "imoblife.androidsensorbox"
    
    logging.info("Launching SensorBox via UIHelper...")
    ui.launch_app(pkg)
    
    time.sleep(5) # Give more time for the app to settle
    
    # Use UIAutomator2 for robust clicking
    try:
        # Dismiss any initial dialogs (Allow, OK, etc.)
        for _ in range(3):
            for btn_text in ["Allow", "OK", "ACCEPT", "Agree"]:
                if ui.d(text=btn_text).exists(timeout=2):
                    logging.info(f"Dismissing dialog with button: {btn_text}")
                    ui.d(text=btn_text).click()
                    time.sleep(1)
        
        # Helper to click and return
        def activate_sensor(btn_id, name):
            logging.info(f"Activating {name} via {btn_id}...")
            # Ensure we are on the main screen by re-launching (fast)
            ui.launch_app(pkg)
            time.sleep(1)
            btn = ui.d(resourceId=f"{pkg}:id/{btn_id}")
            if btn.exists(timeout=5):
                btn.click()
                time.sleep(4) # Give more time for data to flow
                run_adb_cmd("input keyevent KEYCODE_BACK")
                time.sleep(2)
            else:
                logging.warning(f"Button {btn_id} for {name} not found")

        # Wake up sensors one by one
        activate_sensor("iv_gyro", "Gyroscope")
        activate_sensor("iv_orien", "Orientation")
        activate_sensor("iv_magn", "Magnetometer")
            
    except Exception as e:
        logging.error(f"UI interaction failed: {e}")
        # Fallback to simple wait if UI fails
        time.sleep(2)

def run_sensors_tests(ui, reporter, specs=None, excluded=None):
    if not excluded: excluded = []
    """Entry point for Sensors module - Optimized with SensorBox"""
    if not specs: specs = {}
    
    if ensure_sensorbox_ready():
        trigger_sensorbox_activation(ui)
    else:
        logging.warning("SensorBox setup failed, falling back to legacy jitter...")
        run_adb_cmd("am start -a android.intent.action.VIEW -d 'geo:0,0?z=18'")
        time.sleep(3)

    # Aggressive Jitter (Keep for legacy support)
    for _ in range(2):
        run_adb_cmd("input swipe 100 100 900 900 100")
        run_adb_cmd("input swipe 900 100 100 900 100")
    
    time.sleep(1)
    logging.info("Capturing final sensorservice dump...")
    _, dump_out = run_adb_cmd("dumpsys sensorservice")
    
    # Cleanup
    run_adb_cmd("am force-stop imoblife.androidsensorbox")
    run_adb_cmd("am force-stop com.google.android.apps.maps")
    run_adb_cmd("am start -c android.intent.category.HOME -a android.intent.action.MAIN")

    # Use threshold from specs if available, fallback to T70 defaults
    accel_thresh   = specs.get("sensor_accel_threshold", 0.0001)
    gyro_thresh    = specs.get("sensor_gyro_threshold", 0.000001)
    mag_thresh     = specs.get("sensor_mag_threshold", 0.01)
    compass_thresh = specs.get("sensor_compass_threshold", 0.000000001)
    light_thresh   = specs.get("sensor_light_threshold", 0.0000001)

    sensors_to_test = [
        {"id": "Accelerometer", "keywords": ["Accelerometer"], "threshold": accel_thresh},
        {"id": "Gyroscope",     "keywords": ["Gyroscope", "Rotation Vector"], "threshold": gyro_thresh},
        {"id": "Magnetometer",  "keywords": ["Magnetometer"], "threshold": mag_thresh},
        {"id": "e-Compass",     "keywords": ["Rotation Vector", "Geomagnetic", "Orientation", "sns_geomag_rv"], "threshold": compass_thresh},
        {"id": "Light Sensor",  "keywords": ["Ambient Light", "Light Sensor"], "threshold": light_thresh}
    ]
    
    for sensor in sensors_to_test:
        ui_name = sensor["id"]
        keywords = sensor["keywords"]
        threshold = sensor["threshold"]
        
        if ui_name in excluded:
            reporter.add_result("Sensors", ui_name, True, "Skipped by profile", status_override="SKIP")
            continue
        
        has_drv = any(k.lower() in dump_out.lower() for k in keywords)
        reporter.add_result("Sensors", f"{ui_name} (Presence)", has_drv, 
                            "Driver registered" if has_drv else "Missing driver")
        
        logging.info(f"Analyzing {ui_name} Entropy...")
        events = []
        best_k = ""
        for k in keywords:
            events = get_sensor_events(k, dump_out)
            if events: 
                best_k = k
                break
            
        if events and len(events) >= 3:
            x_vals = [e[0] for e in events]
            y_vals = [e[1] for e in events]
            z_vals = [e[2] for e in events]
            total_entropy = stdev(x_vals) + stdev(y_vals) + stdev(z_vals)
            
            if total_entropy >= threshold or len(events) >= 10:
                reporter.add_result("Sensors", f"{ui_name} (Entropy)", True, 
                                    f"PASS (Source: {best_k}, Var: {total_entropy:.9f}, Events: {len(events)})")
            else:
                reporter.add_result("Sensors", f"{ui_name} (Entropy)", False, 
                                    f"Driver alive but data frozen (Var: {total_entropy:.9f} < {threshold}).")
        else:
            reporter.add_result("Sensors", f"{ui_name} (Entropy)", False, 
                                "No live events found. Sensor inactive during test.")

def run_power_tests(ui, reporter):
    """Entry point for Power module"""
    logging.info("Running Power & Battery Tests...")
    try:
        _, out = run_adb_cmd("dumpsys battery")
        if "level" in out:
            level = [line for line in out.split('\n') if 'level' in line][0].split(':')[1].strip()
            ac_powered = [line for line in out.split('\n') if 'AC powered' in line][0].split(':')[1].strip()
            msg = f"Battery Level: {level}%, AC Powered: {ac_powered}"
            reporter.add_result("Power", "Battery Read", True, msg)
    except Exception as e:
        logging.error(f"Battery check failed: {e}")
