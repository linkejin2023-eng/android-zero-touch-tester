from framework.adb_helper import run_adb_cmd
from framework.ui_automator import UIHelper
from framework.report_generator import HTMLReportGenerator
import logging

def run_tests(ui: UIHelper, reporter: HTMLReportGenerator):
    logging.info("Running Sensor & System Tests...")
    
    # Sensors Check (Gyro, Light, Accel)
    try:
        code, out = run_adb_cmd("dumpsys sensorservice")
        
        # Look for standard sensors
        has_accel = "Accelerometer" in out or "ACCELEROMETER" in out
        has_gyro = "Gyroscope" in out or "GYROSCOPE" in out
        has_light = "Light" in out or "LIGHT" in out
        
        reporter.add_result("Sensors", "Accelerometer", has_accel, "Accelerometer driver detected" if has_accel else "Missing Accelerometer")
        reporter.add_result("Sensors", "Gyroscope", has_gyro, "Gyroscope driver detected" if has_gyro else "Missing Gyroscope")
        reporter.add_result("Sensors", "Light Sensor", has_light, "Light sensor driver detected" if has_light else "Missing Light sensor")
        
    except Exception as e:
        reporter.add_result("Sensors", "Sensor Service Check", False, str(e))
        
    # Battery & Power
    try:
        code, out = run_adb_cmd("dumpsys battery")
        
        if "level" in out and "AC powered" in out:
            level = [line for line in out.split('\n') if 'level' in line][0].split(':')[1].strip()
            ac_powered = [line for line in out.split('\n') if 'AC powered' in line][0].split(':')[1].strip()
            
            msg = f"Battery Level: {level}%, AC Powered: {ac_powered}"
            reporter.add_result("Power", "Battery Read", True, msg)
            
            # Simulated Unplug
            if ac_powered == "true":
                run_adb_cmd("dumpsys battery set ac 0")
                run_adb_cmd("dumpsys battery set usb 0")
                code, check_out = run_adb_cmd("dumpsys battery | grep 'AC powered'")
                if "false" in check_out:
                    reporter.add_result("Power", "Battery Unplug Simulation", True, "Successfully simulated AC unplug")
                else:
                    reporter.add_result("Power", "Battery Unplug Simulation", False, "Failed to simulate AC unplug")
                # Reset
                run_adb_cmd("dumpsys battery reset")
        else:
            reporter.add_result("Power", "Battery Config", False, "Failed to read standard battery properties")
    except Exception as e:
        reporter.add_result("Power", "Battery check", False, str(e))

    # Touchscreen Input Check
    try:
        # Check if input devices report a touch screen
        code, out = run_adb_cmd("dumpsys input")
        if "Touch" in out or "touch" in out.lower() or "event" in out:
            reporter.add_result("Touchscreen", "Input Device Listing", True, "Found registered touch/input devices")
        else:
            reporter.add_result("Touchscreen", "Input Device Listing", False, "No touch devices registered in InputManager")
    except Exception as e:
        reporter.add_result("Touchscreen", "Input Device Listing", False, str(e))
