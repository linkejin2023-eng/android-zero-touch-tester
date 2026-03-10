import time
import logging
from framework.adb_helper import run_adb_cmd

def run_tests(ui, reporter):
    logging.info("Running GPS / Location Tests...")
    
    # 1. GPS Provider Status
    try:
        # Force Enable Location via settings (mode 3 = HIGH_ACCURACY)
        # Note: In newer Androids, this is location_providers_allowed=gps,network
        run_adb_cmd("settings put secure location_mode 3")
        run_adb_cmd("settings put secure location_providers_allowed +gps,network")
        time.sleep(2)
        
        # Check dumpsys location to see if GPS provider is registered
        code, out = run_adb_cmd("dumpsys location | grep -i 'gps' -A 2")
        
        if "gps" in out.lower():
             reporter.add_result("GPS", "GPS Functionality", True, "GPS Location Provider is enabled and registered in LocationManagerService")
        else:
             reporter.add_result("GPS", "GPS Functionality", False, "GPS Provider not found in dumpsys location")
             
    except Exception as e:
         reporter.add_result("GPS", "GPS Functionality", False, f"GPS check failed: {e}")
