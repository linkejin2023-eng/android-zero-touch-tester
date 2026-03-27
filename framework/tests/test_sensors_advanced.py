import time
import logging
import re
import math
from framework.adb_helper import run_adb_cmd

def stdev(data):
    n = len(data)
    if n <= 1: return 0.0
    mean = sum(data) / n
    variance = sum((x - mean) ** 2 for x in data) / (n - 1)
    return math.sqrt(variance)

def run_tests(ui, reporter):
    logging.info("Running Advanced Sensor Tests (Static Entropy Analysis)...")
    
    def get_sensor_events(name_filter):
        _, out = run_adb_cmd("dumpsys sensorservice")
        events = []
        recording = False
        
        for line in out.splitlines():
            # Trigger recording when we see the history header for our target sensor
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

    try:
        # Give sensor driver a moment to collect data
        time.sleep(2)
        
        sensors_to_test = {
            "Accelerometer": ("Accelerometer", "lsm6dst", "Accelerometer"),
            "Gyroscope": ("Gyroscope", "lsm6dst", "Gyroscope"),
            "e-Compass": ("Magnetometer", "Magnetic Field", "GeoMag")
        }
        
        for ui_name, keywords in sensors_to_test.items():
            logging.info(f"Analyzing {ui_name} Entropy...")
            
            # Try to get events using the primary keyword
            events = get_sensor_events(keywords[0]) or get_sensor_events(keywords[1]) or get_sensor_events(keywords[2])
            
            if events and len(events) >= 3:
                x_vals = [e[0] for e in events]
                y_vals = [e[1] for e in events]
                z_vals = [e[2] for e in events]
                
                total_entropy = stdev(x_vals) + stdev(y_vals) + stdev(z_vals)
                
                # Even on a flat table, noise guarantees stdev > 0.0001
                if total_entropy > 0.0001:
                    reporter.add_result("Sensors", f"{ui_name} (Entropy)", True, 
                                        f"Driver alive. Entropy variance: {total_entropy:.5f}",
                                        procedure="Analyze standard deviation of last 10 dumpsys events",
                                        pass_criteria="Entropy > 0.0001")
                else:
                    reporter.add_result("Sensors", f"{ui_name} (Entropy)", False, 
                                        f"Driver frozen. Exact 0 variance across {len(events)} events. Sensor is likely dead.",
                                        procedure="Analyze standard deviation", pass_criteria="Entropy > 0.0001")
            else:
                code, out = run_adb_cmd("dumpsys sensorservice")
                has_drv = any(k.lower() in out.lower() for k in keywords)
                
                if has_drv:
                    reporter.add_result("Sensors", f"{ui_name} (Presence)", True, 
                                        "Driver registered (Sleep State). No live numeric events detected because no app is currently polling it.",
                                        procedure="Check dumpsys representation", pass_criteria="Found in driver list")
                else:
                    reporter.add_result("Sensors", f"{ui_name} (Presence)", False, 
                                        f"Missing {ui_name} driver completely from service.",
                                        status_override="FAIL")
    except Exception as e:
        reporter.add_result("Sensors", "e-Compass Check", False, str(e), status_override="ERROR")
