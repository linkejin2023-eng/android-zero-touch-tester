import time
import logging
from framework.adb_helper import run_adb_cmd

def run_tests(ui, reporter):
    logging.info("Running Advanced Sensor Tests...")
    
    # Advanced Sensors (Dynamic)
    def get_latest_sensor_event(name_filter):
        _, out = run_adb_cmd("dumpsys sensorservice")
        blocks = []
        current_block = []
        import re
        header_re = re.compile(r'^[a-zA-Z0-9_ ]+ \(handle=0x')
        for line in out.splitlines():
            if header_re.match(line):
                if current_block: blocks.append('\n'.join(current_block))
                current_block = [line]
            else:
                current_block.append(line)
        if current_block: blocks.append('\n'.join(current_block))
            
        for block in blocks:
            header = block.split('\n')[0]
            if name_filter.lower() in header.lower():
                if "last 10 events" in block:
                    lines = block.split('\n')
                    latest_data = None
                    history_found = False
                    for line in lines:
                        if "last 10 events" in line: history_found = True
                        if history_found and "(" in line and ")" in line and "," in line:
                            data = line.split(")")[-1].strip()
                            if data.count(',') >= 2: latest_data = data
                    if latest_data: return latest_data
        return None

    try:
        logging.info("Sampling Magnetometer (T0)...")
        mag_t0 = get_latest_sensor_event("Magnetometer") or get_latest_sensor_event("Magnetic")
        
        time.sleep(2)
        
        logging.info("Sampling Magnetometer (T1)...")
        mag_t1 = get_latest_sensor_event("Magnetometer") or get_latest_sensor_event("Magnetic")
        
        if mag_t0 and mag_t1:
            if mag_t0 != mag_t1:
                reporter.add_result("Sensors", "e-Compass (Dynamic)", True, f"Verified: Magnetic field changing ({mag_t1})")
            else:
                reporter.add_result("Sensors", "e-Compass (Dynamic)", False, f"Failed: Data frozen ({mag_t1}). Ensure device is rotating.")
        else:
            code, out = run_adb_cmd("dumpsys sensorservice")
            has_mag = any(k in out for k in ["Magnetometer", "Magnetic Field", "GeoMag"])
            reporter.add_result("Sensors", "e-Compass (Presence)", has_mag, "Driver detected but no live events" if has_mag else "Missing Magnetometer")
    except Exception as e:
        reporter.add_result("Sensors", "e-Compass Check", False, str(e))
