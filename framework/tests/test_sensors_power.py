from framework.adb_helper import run_adb_cmd
from framework.ui_automator import UIHelper
from framework.report_generator import HTMLReportGenerator
import logging

def run_tests(ui: UIHelper, reporter: HTMLReportGenerator):
    logging.info("Running Sensor & System Tests...")
    
    # Sensors Check (Dynamic Data Verification)
    def get_latest_sensor_event(name_filter):
        _, out = run_adb_cmd("dumpsys sensorservice")
        # Split by lines and manually group blocks by header.
        # Sensors start with: Name (handle=0x..., connections=...)
        blocks = []
        current_block = []
        import re
        header_re = re.compile(r'^[a-zA-Z0-9_ ]+ \(handle=0x')
        
        for line in out.splitlines():
            if header_re.match(line):
                if current_block:
                    blocks.append('\n'.join(current_block))
                current_block = [line]
            else:
                current_block.append(line)
        if current_block:
            blocks.append('\n'.join(current_block))
            
        for block in blocks:
            header = block.split('\n')[0]
            if name_filter.lower() in header.lower():
                if "last 10 events" in block:
                    lines = block.split('\n')
                    latest_data = None
                    history_found = False
                    for line in lines:
                        if "last 10 events" in line:
                            history_found = True
                        if history_found and "(" in line and ")" in line and "," in line:
                            data = line.split(")")[-1].strip()
                            if data.count(',') >= 2:
                                latest_data = data
                    if latest_data:
                        return latest_data
        return None

    try:
        logging.info("Sampling sensor data (T0)...")
        # Use more specific names for STMicro and Qualcomm sensors on T70
        accel_t0 = get_latest_sensor_event("Accelerometer")
        gyro_t0 = get_latest_sensor_event("Gyroscope")
        mag_t0 = get_latest_sensor_event("Magnetometer") or get_latest_sensor_event("Magnetic")
        
        import time
        time.sleep(3) # Wait for device movement (swinging platform)
        
        logging.info("Sampling sensor data (T1)...")
        accel_t1 = get_latest_sensor_event("Accelerometer")
        gyro_t1 = get_latest_sensor_event("Gyroscope")
        mag_t1 = get_latest_sensor_event("Magnetometer") or get_latest_sensor_event("Magnetic")
        
        # Verify Accelerometer
        if accel_t0 and accel_t1:
             if accel_t0 != accel_t1:
                 reporter.add_result("Sensors", "Accelerometer (Dynamic)", True, f"Verified: Data is changing ({accel_t1})")
             else:
                 reporter.add_result("Sensors", "Accelerometer (Dynamic)", False, f"Failed: Data is frozen/static ({accel_t1}). Ensure device is moving.")
        else:
             # Fallback to driver presence
             code, out = run_adb_cmd("dumpsys sensorservice")
             has_accel = "Accelerometer" in out or "ACCELEROMETER" in out
             reporter.add_result("Sensors", "Accelerometer (Presence)", has_accel, "Driver detected but no live events found" if has_accel else "Missing driver")

        # Verify Gyroscope
        if gyro_t0 and gyro_t1:
             if gyro_t0 != gyro_t1:
                 reporter.add_result("Sensors", "Gyroscope (Dynamic)", True, f"Verified: Data is changing ({gyro_t1})")
             else:
                 reporter.add_result("Sensors", "Gyroscope (Dynamic)", False, f"Failed: Data is frozen/static ({gyro_t1})")
        else:
             code, out = run_adb_cmd("dumpsys sensorservice")
             has_gyro = "Gyroscope" in out or "GYROSCOPE" in out
             reporter.add_result("Sensors", "Gyroscope (Presence)", has_gyro, "Driver detected but no live events found" if has_gyro else "Missing driver")

        # Verify Magnetometer
        if mag_t0 and mag_t1:
             if mag_t0 != mag_t1:
                 reporter.add_result("Sensors", "Magnetometer (Dynamic)", True, f"Verified: Magnetic field changing ({mag_t1})")
             else:
                 reporter.add_result("Sensors", "Magnetometer (Dynamic)", False, f"Failed: Magnetic data frozen ({mag_t1})")
        else:
             code, out = run_adb_cmd("dumpsys sensorservice")
             has_mag = "Magnetometer" in out or "MAGNETOMETER" in out or "Magnetic field" in out
             reporter.add_result("Sensors", "Magnetometer (Presence)", has_mag, "Driver detected but no live events found" if has_mag else "Missing driver")

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

