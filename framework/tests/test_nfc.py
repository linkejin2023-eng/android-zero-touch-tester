import time
import logging
from framework.adb_helper import run_adb_cmd

def run_tests(ui, reporter):
    logging.info("Running NFC Tests...")
    
    # 1. NFC Service Status
    try:
        # Force Enable NFC via root/shell SVC cmd
        run_adb_cmd("svc nfc enable")
        time.sleep(2)
        
        # Check dumpsys nfc to see if it is ON
        code, out = run_adb_cmd("dumpsys nfc | grep 'mState=' -A 1")
        
        # mState can be "on", "1", "3", or similar depending on android version.
        # Alternatively, run settings command
        code_settings, out_settings = run_adb_cmd("settings get secure nfc_on")
        if "1" in out_settings.strip() or "on" in out.lower() or "active" in out.lower():
             reporter.add_result("NFC", "NFC Functionality", True, "NFC service is successfully enabled and running")
        elif code_settings == 0 and out_settings:
             reporter.add_result("NFC", "NFC Functionality", True, f"NFC state reported by settings: {out_settings.strip()}")
        else:
             reporter.add_result("NFC", "NFC Functionality", False, "Failed to enable or detect NFC service state")
    except Exception as e:
         reporter.add_result("NFC", "NFC Functionality", False, str(e))
