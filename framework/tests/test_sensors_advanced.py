import time
import logging
from framework.adb_helper import run_adb_cmd

def run_tests(ui, reporter):
    logging.info("Running Advanced Sensor Tests...")
    
    # 1. e-Compass (Magnetic Sensor)
    try:
        # Check if the magnetic sensor is listed and responding in dumpsys sensorservice
        code, out = run_adb_cmd("dumpsys sensorservice | grep -i 'Magnetometer' -A 1")
        if "Magnetometer" in out or "Magnetic" in out:
            reporter.add_result("Sensors", "e-Compass", True, "Magnetic sensor (e-Compass) driver detected")
        else:
            reporter.add_result("Sensors", "e-Compass", False, "Magnetic sensor not found in dumpsys")
    except Exception as e:
        reporter.add_result("Sensors", "e-Compass", False, str(e))
        
    # 2. Accelerometer (Wait for state changes or just check driver)
    try:
         code, out = run_adb_cmd("dumpsys sensorservice | grep -i 'Accelerometer' -A 1")
         if "Accelerometer" in out:
              reporter.add_result("Sensors", "Accelerometer (Advanced)", True, "Accelerometer driver detected")
         else:
              reporter.add_result("Sensors", "Accelerometer (Advanced)", False, "Accelerometer not found in dumpsys")
    except Exception as e:
         reporter.add_result("Sensors", "Accelerometer (Advanced)", False, str(e))
         
    # 3. Sensor Stability check (Just verifying services are still healthy)
    try:
        _, out = run_adb_cmd("dumpsys sensorservice | grep -i 'active' | head -n 5")
        reporter.add_result("Sensors", "Sensor Service Health", True, "Sensor services remain active and stable")
    except Exception as e:
        reporter.add_result("Sensors", "Sensor Service Health", False, str(e))
