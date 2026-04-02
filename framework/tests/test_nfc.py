import time
import logging
from framework.adb_helper import run_adb_cmd

def run_tests(ui, reporter):
    """
    NFC Test with robust polling and power cycling to detect static/taped tags.
    """
    logging.info("Running NFC Tests (Robust Detection)...")
    NFC_TIMEOUT = 30 # Extended timeout for T70 re-poll stabilization
    
    # 1. NFC Service Power Cycle
    # Clearing logcat and cycling service to force a fresh tag discovery event
    try:
        logging.info("Cycling NFC power & clearing logs for fresh detection...")
        run_adb_cmd("svc nfc disable")
        time.sleep(2)
        run_adb_cmd("logcat -c") # Clear buffer to avoid stale detection
        run_adb_cmd("svc nfc enable")
        
        # Verify if service is actually UP before polling
        is_ready = False
        for _ in range(5):
            _, out_dump = run_adb_cmd("dumpsys nfc | grep 'mState='")
            if "on" in out_dump.lower() or "3" in out_dump:
                is_ready = True
                break
            time.sleep(1)
        
        if is_ready:
            reporter.add_result("NFC", "NFC Power Cycle", True, "NFC service enabled and polling started")
        else:
            reporter.add_result("NFC", "NFC Power Cycle", False, "NFC failed to reach 'ON' state")
            return # Abort if service is dead
            
    except Exception as e:
        reporter.add_result("NFC", "NFC Power Cycle", False, str(e))
        return

    # 2. Physical Tag Read Verification (Polling Loop)
    found_tag = False
    details = "No tag detected"
    
    logging.info(f"--- NFC Tag Polling (Max {NFC_TIMEOUT}s) ---")
    start_time = time.time()
    
    try:
        while (time.time() - start_time) < NFC_TIMEOUT:
            # Check Logcat for Discovery Intents or Native events
            # We look for ACTIONs or NativeNfcTag/Tag discovered strings
            _, out_log = run_adb_cmd("logcat -d | grep -iE 'ACTION_NDEF_DISCOVERED|ACTION_TECH_DISCOVERED|ACTION_TAG_DISCOVERED|NativeNfcTag: Connect|Tag discovered'")
            
            if out_log.strip():
                details = f"Verified via Logcat: {out_log.splitlines()[-1]}"
                found_tag = True
                break
            
            # Check Dumpsys as fallback (mLastTag contains historical discovery)
            _, nfc_sys = run_adb_cmd("dumpsys nfc | grep -i 'mLastTag'")
            if "null" not in nfc_sys.lower() and nfc_sys.strip():
                details = f"Verified via Dumpsys History: {nfc_sys.strip()}"
                found_tag = True
                break
                
            time.sleep(1.5)
            elapsed = int(time.time() - start_time)
            if elapsed % 5 == 0:
                logging.info(f"Still polling for NFC Tag... ({elapsed}/{NFC_TIMEOUT}s)")

        if found_tag:
            reporter.add_result("NFC", "Tag Read Verification", True, details)
            logging.info(f"NFC Tag successfully detected after {int(time.time() - start_time)}s.")
        else:
            reporter.add_result("NFC", "Tag Read Verification", False, 
                                f"Failed: No tag detected after {NFC_TIMEOUT}s. Ensure Tag is on the induction area.")
                
    except Exception as e:
        reporter.add_result("NFC", "Tag Read Verification", False, str(e))
