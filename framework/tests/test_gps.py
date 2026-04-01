import time
import logging
from framework.adb_helper import run_adb_cmd

def run_tests(ui, reporter):
    logging.info("Running GPS / Location Tests...")
    
    # 1. GPS Provider Status
    try:
        # 1. Force Enable Location via Modern CMD (Android 10+)
        run_adb_cmd("cmd location set-location-enabled true")
        time.sleep(1)
        
        # Grant permissions to Maps to avoid OOBE dialogs blocking the session
        logging.info("Granting location permissions to Maps...")
        run_adb_cmd("pm grant com.google.android.apps.maps android.permission.ACCESS_FINE_LOCATION")
        run_adb_cmd("pm grant com.google.android.apps.maps android.permission.ACCESS_COARSE_LOCATION")
        
        # Trigger a location scan by calling Google Maps or generic geo intent
        # This wakes up the GNSS hardware which otherwise stays idle
        logging.info("Triggering GPS session via Maps/Intent...")
        # Force start with clear stack to ensure it requests fresh location
        code, _ = run_adb_cmd("am start -S -n com.google.android.apps.maps/com.google.android.maps.MapsActivity")
        if code != 0:
            run_adb_cmd("am start -a android.intent.action.VIEW -d 'geo:0,0?q=location'")
        
        # 1. Provider Registration Check
        code, out = run_adb_cmd("dumpsys location")
        
        provider_ok = "gps" in out.lower()
        if not provider_ok:
            reporter.add_result("GPS", "GPS Provider", False, "GPS Provider not found in dumpsys location")
            return
            
        reporter.add_result("GPS", "GPS Provider", True, "GPS Location Provider is successfully registered")
        
        # 2. Hardware Signal Check (Weak Signal Tolerance)
        # Give hardware time to acquire initial SV data (increased to 60s for indoors)
        logging.info("Waiting for GPS hardware to scan satellites (60s)...")
        time.sleep(60)
        
        _, out = run_adb_cmd("dumpsys location")
        # Look for satellite indicators in dumpsys
        sv_count = 0
        import re
        
        # Check both legacy and modern indicators
        # Snr pattern (e.g., snrs=[22.0, 15.0...]) or CN0 is the most authoritative
        for line in out.split("\n"):
            # Variant A: mSvCount=5 or Satellites: 5
            sv_match = re.search(r'(?:mSvCount|Satellites|mSatellites)=?[:\s]*(\d+)', line, re.IGNORECASE)
            if sv_match:
                try: sv_count = max(sv_count, int(sv_match.group(1)))
                except: pass
            
            # Variant B: Trimble T70 / GNSS_KPI messages
            kpi_match = re.search(r'Total number of (?:sv status messages|CN0 reports) processed:\s*(\d+)', line, re.IGNORECASE)
            if kpi_match:
                try: 
                    if int(kpi_match.group(1)) > 0: sv_count = max(sv_count, 1)
                except: pass

            # Variant C: Raw SNRs (Most robust)
            snr_match = re.search(r'snrs?=\[([\d\.\,\s]+)\]', line, re.IGNORECASE)
            if snr_match:
                snrs = [float(x.strip()) for x in snr_match.group(1).split(",") if x.strip()]
                sv_count = max(sv_count, len([s for s in snrs if s > 0]))
        
        # Cleanup: Close the trigger app (Home screen)
        run_adb_cmd("input keyevent 3")



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
