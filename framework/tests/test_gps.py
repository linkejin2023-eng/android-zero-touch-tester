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
        
        # 1. Provider Registration Check
        code, out = run_adb_cmd("dumpsys location")
        
        provider_ok = False
        parts = out.split("\n")
        for line in parts:
            if "gps" in line.lower() and "provider" in line.lower():
                provider_ok = True
                break
                
        if not provider_ok:
            reporter.add_result("GPS", "GPS Provider", False, "GPS Provider not found in dumpsys location")
            return
            
        reporter.add_result("GPS", "GPS Provider", True, "GPS Location Provider is successfully registered")
        
        # 2. Hardware Signal Check (Weak Signal Tolerance)
        logging.info("Waiting for GPS hardware to scan satellites (10s)...")
        time.sleep(10)
        
        _, out = run_adb_cmd("dumpsys location")
        # Look for satellite indicators in dumpsys
        sv_count = 0
        import re
        
        for line in out.split("\n"):
            # Example: mSvCount=5 or Satellites: 5
            sv_match = re.search(r'(?:mSvCount|Satellites|mSatellites)=?[:\s]*(\d+)', line, re.IGNORECASE)
            if sv_match:
                try:
                    count = int(sv_match.group(1))
                    sv_count = max(sv_count, count)
                except ValueError:
                    pass
            # Trimble T70 / Some Android 10+ devices log under GNSS_KPI
            kpi_match = re.search(r'Total number of sv status messages processed:\s*(\d+)', line, re.IGNORECASE)
            if kpi_match:
                try:
                    count = int(kpi_match.group(1))
                    if count > 0: sv_count = max(sv_count, 1) # If it processed messages, signal is alive
                except ValueError:
                    pass
            # Example: snrs=[22.0, 15.0, 0.0...]
            snr_match = re.search(r'snrs?=\[([\d\.\,\s]+)\]', line, re.IGNORECASE)
            if snr_match:
                snrs = [float(x.strip()) for x in snr_match.group(1).split(",") if x.strip()]
                sv_count = max(sv_count, len([s for s in snrs if s > 0]))

        if sv_count > 0:
            reporter.add_result("GPS", "GPS Antenna Signal", True, 
                                f"Hardware OK (Weak Signal Tolerance). Detected {sv_count} satellites without full fix.",
                                procedure="Parse dumpsys location for SV count/SNR", pass_criteria="SV Count > 0")
        else:
            reporter.add_result("GPS", "GPS Antenna Signal", False, 
                                "No satellites detected. Ensure device is not completely shielded.",
                                procedure="Parse dumpsys location for SV count/SNR", pass_criteria="SV Count > 0")
             
    except Exception as e:
         reporter.add_result("GPS", "GPS Functionality", False, f"GPS check failed: {e}", status_override="ERROR")
