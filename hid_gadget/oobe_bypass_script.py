try:
    from .aoa_driver import AOADriver, KB_REPORT_DESC, CONSUMER_REPORT_DESC
except (ImportError, ValueError):
    from aoa_driver import AOADriver, KB_REPORT_DESC, CONSUMER_REPORT_DESC
import time
import logging
import subprocess

# HID Keycodes (partial list)
KEY_NONE = 0x00
KEY_A = 0x04
KEY_B = 0x05
KEY_C = 0x06
# ...
KEY_ENTER = 0x28
KEY_ESC = 0x29
KEY_BACKSPACE = 0x2a
KEY_TAB = 0x2b
KEY_SPACE = 0x2c
# Alphabetic keys for shortcuts
KEY_I = 0x0c
KEY_N = 0x11
KEY_D = 0x07
KEY_H = 0x0b
# Navigation
KEY_RIGHT = 0x4f
KEY_LEFT = 0x50
KEY_DOWN = 0x51
KEY_UP = 0x52
KEY_PAGEUP = 0x4b
KEY_PAGEDOWN = 0x4e

# Modifiers
MOD_LCTRL = 0x01
MOD_LSHIFT = 0x02
MOD_LALT = 0x04
MOD_LMETA = 0x08

class OOBEBypass:
    def __init__(self, driver):
        self.driver = driver
        self.hid_kb_id = 1
        self.hid_consumer_id = 2

    def press_key(self, keycode, modifier=KEY_NONE, duration=0.05):
        """Sends a standard keyboard key press and release event (HID ID 1)."""
        press_report = bytearray([modifier, 0, keycode, 0, 0, 0, 0, 0])
        if not self.driver.send_hid_event(self.hid_kb_id, press_report):
            return False
        time.sleep(duration)
        
        release_report = bytearray([0, 0, 0, 0, 0, 0, 0, 0])
        self.driver.send_hid_event(self.hid_kb_id, release_report)
        time.sleep(duration)
        return True

    def press_home(self, duration=0.05):
        """Sends a Consumer Page Home event (0x0223) - HID ID 2."""
        # 16-bit Usage ID in Little-Endian: 0x0223 -> [0x23, 0x02]
        press_report = bytearray([0x23, 0x02])
        if not self.driver.send_hid_event(self.hid_consumer_id, press_report):
            return False
        time.sleep(duration)
        
        # Release (Send 0x0000)
        release_report = bytearray([0x00, 0x00])
        self.driver.send_hid_event(self.hid_consumer_id, release_report)
        time.sleep(duration)
        return True

    def press_back(self, duration=0.05):
        """Sends a Consumer Page Back event (0x0224) - HID ID 2."""
        # 16-bit Usage ID in Little-Endian: 0x0224 -> [0x24, 0x02]
        press_report = bytearray([0x24, 0x02])
        if not self.driver.send_hid_event(self.hid_consumer_id, press_report):
            return False
        time.sleep(duration)
        
        release_report = bytearray([0x00, 0x00])
        self.driver.send_hid_event(self.hid_consumer_id, release_report)
        time.sleep(duration)
        return True

    def enable_adb_trimble(self, sku="gms"):
        """Automates the full ADB enablement sequence including re-enumeration handling."""
        logging.info(f"Starting ADB Enablement sequence (Trimble T70, SKU={sku})...")
        
        # [Optimization] For userdebug/authorized devices: Skip HID sequence if ADB is already ready
        def is_adb_ready_now():
            try:
                out = subprocess.check_output(["adb", "devices"]).decode()
                return "\tdevice" in out
            except:
                return False

        if is_adb_ready_now():
            logging.info("ADB already ready. Forcing 'Developer Options' enabled and skipping HID clicks.")
            try:
                subprocess.run(["adb", "shell", "settings", "put", "global", "development_settings_enabled", "1"], capture_output=True)
                subprocess.run(["adb", "shell", "settings", "put", "global", "adb_enabled", "1"], capture_output=True)
                logging.info("Developer Options forced ON via ADB command.")
            except:
                pass
            return # Skip the entire HID sequence!
        
        # We start exactly from where the recorder left off (assuming Home Screen)
        hybrid_seq = [
            "SETTINGS", 
        ]
        
        # China SKU needs extra steps to dismiss initial agreement/prompt when opening settings
        if sku == "china":
            hybrid_seq.extend(["TAB", "TAB", "ENTER"])
            
        # Toggle ADB: China SKU has 6 DOWNs (GMS has 7)
        adb_toggle_downs = ["DOWN"] * (6 if sku == "china" else 7)
        
        # Second set of DOWNs to reach the final toggle/confirmation: China SKU has 12 (GMS has 14)
        final_toggle_downs = ["DOWN"] * (12 if sku == "china" else 14)
        
        hybrid_seq.extend([
            "TAB", "TAB", "TAB", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", 
            "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "ENTER", # Enters About Phone?
            "TAB", "TAB", "TAB", "TAB", "TAB", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", 
            "TAB", "TAB", "TAB", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "ENTER", # Build number?
            "MULTI_ENTER", "SYS_BACK", "UP", "ENTER", # Dev options
            "TAB"
        ] + adb_toggle_downs + [
            "ENTER", # Toggle ADB
            "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB"
        ] + final_toggle_downs + [
            "ENTER", "TAB", "TAB", "ENTER"
        ])

        for cmd in hybrid_seq:
            try:
                if cmd == "SETTINGS":
                    self.press_key(KEY_I, MOD_LMETA)
                    time.sleep(2.0) # Slightly more delay for China SKU settings load
                elif cmd == "TAB": self.press_key(KEY_TAB)
                elif cmd == "ENTER": 
                    self.press_key(KEY_ENTER)
                    time.sleep(2) # Give UI time to react
                elif cmd == "DOWN": 
                    self.press_key(KEY_DOWN)
                    time.sleep(0.2)
                elif cmd == "UP": 
                    self.press_key(KEY_UP)
                    time.sleep(0.2)
                elif cmd == "MULTI_ENTER": 
                    for _ in range(7):
                        self.press_key(KEY_ENTER)
                        time.sleep(0.1)
                    time.sleep(1.0) # Delay to allow "You are now a developer" toast/transition
                elif cmd == "SYS_BACK": 
                    self.press_back()
                    time.sleep(1.0) # Delay for back navigation transition
                elif cmd == "SYS_HOME": 
                    self.press_home()
                
                logging.info(f"HID Event Sent: {cmd}")
            except Exception as e:
                # If we lose connection here (e.g. PID changed), we exit loop and handle reconnection
                if "No such device" in str(e) or "Pipe error" in str(e):
                    logging.warning("Device disconnected (likely PID change). Starting reconnection...")
                    break
        
        # 3. Handle Re-enumeration
        time.sleep(5) # Wait for device to re-appear with 02B5
        logging.info("Attempting to reconnect after ADB toggle...")
        
        # Explicitly search for the device again (PID changed!)
        if self.driver.find_device():
            if self.driver.switch_to_accessory_mode():
                self.driver.register_hid(1, KB_REPORT_DESC)
                self.driver.register_hid(2, CONSUMER_REPORT_DESC)
                
                logging.info("Re-connected! Sending final 'Allow USB Debugging' sequence...")
                
                def is_adb_authorized():
                    try:
                        import subprocess
                        out = subprocess.check_output(["adb", "devices"]).decode()
                        return "DBB123456789\tdevice" in out or "\tdevice" in out
                    except:
                        return False

                # Try a few times in case the dialog is slow, but stop if authorized
                for attempt in range(3):
                    if is_adb_authorized():
                        logging.info("ADB recognized. Forcing 'Developer Options' menu enabled via ADB...")
                        try:
                            # 1. 開啟開發人員選項選單
                            subprocess.run(["adb", "shell", "settings", "put", "global", "development_settings_enabled", "1"], capture_output=True)
                            # 2. 確保 ADB 偵錯是開啟的 (雖然通常已開)
                            subprocess.run(["adb", "shell", "settings", "put", "global", "adb_enabled", "1"], capture_output=True)
                            logging.info("Developer Options & ADB menu forced ON.")
                        except Exception as ex:
                            logging.warning(f"Failed to force settings via ADB: {ex}")
                        break
                        
                    logging.info(f"Authorization attempt {attempt + 1}...")
                    self.press_key(KEY_ENTER) # Dismiss focus
                    time.sleep(0.5)
                    self.press_key(KEY_TAB)
                    self.press_key(KEY_TAB)
                    self.press_key(KEY_ENTER)
                    time.sleep(3) # Delay to allow ADB state change
                
                logging.info("ADB Enablement Step Finished.")
            else:
                logging.error("Failed to re-switch to Accessory Mode.")
        else:
            logging.error("Failed to find device after PID change.")

    def type_string(self, text):
        """Simple string typer (lowercase only for now)."""
        for char in text.lower():
            if 'a' <= char <= 'z':
                keycode = ord(char) - ord('a') + 4
                self.press_key(keycode)
            elif char == ' ':
                self.press_key(KEY_SPACE)
            time.sleep(0.05)

    def bypass_gms_oobe(self, has_sim=True):
        logging.info(f"Executing GMS OOBE Bypass (has_sim={has_sim}) for Trimble T70...")
        
        # Base sequence up to Offline Setup
        sequence = [
            "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "ENTER", # Welcome screen (5x DOWN to target Start)
            "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "ENTER", # Wi-Fi Skip
            "TAB", "TAB", "ENTER", # Offline setup confirmation
        ]

        if not has_sim:
            # Date & Time page only appears WITHOUT SIM
            sequence.extend(["TAB", "TAB", "TAB", "TAB", "ENTER"])

        # PIN Screen + Confirm dialog
        sequence.extend([
            "SYS_BACK", "TAB", "ENTER",      # PIN Screen Skip (BACK to hide keyboard, TAB to focus Skip)
            "SLEEP_1", "TAB", "TAB", "ENTER", # Skip anyway dialog
            "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "ENTER" # Google Services
        ])
        
        self._execute_sequence(sequence)

    def bypass_china_oobe(self):
        logging.info("Starting China SKU OOBE Bypass sequence for Trimble T70...")
        
        # Sequence provided by user for China SKU
        sequence = [
            "TAB", "TAB", "ENTER", # Welcome screen / Language?
            "TAB", "TAB", "TAB", "TAB", "TAB", "ENTER" # China specific Skip flow
        ]
        self._execute_sequence(sequence)

        logging.info("Recovery HID Reset sequence delivered.")

    def reset_via_recovery_adb(self):
        """Tier 2: Industrial ADB-based reset while in Recovery mode.
        Much more reliable than HID navigation for T70.
        """
        logging.info("Starting Recovery ADB Reset Sequence...")
        try:
            # 1. Elevate to root if possible
            subprocess.run(["adb", "root"], capture_output=True)
            time.sleep(2)
            
            # 2. Execute the official recovery wipe command
            logging.info("Sending 'recovery --wipe_data' command...")
            result = subprocess.run(
                ["adb", "shell", "recovery", "--wipe_data"],
                capture_output=True, text=True, timeout=15
            )
            
            if result.returncode == 0 or "rebooting" in result.stdout.lower():
                logging.info("Wipe command accepted. Device should reboot shortly.")
                return True
            else:
                logging.error(f"Recovery wipe command failed: {result.stderr}")
                return False
        except Exception as e:
            logging.error(f"Error during Recovery ADB reset: {e}")
            return False

    def _clean_and_dismiss_popups(self, d):
        """Pre-navigation cleanup: Dismiss known popups and return to a clean Home state."""
        logging.info("Performing pre-navigation cleanup...")
        
        # 1. Handle Trimble Touch Firmware Update Popup (YES/NO)
        for _ in range(3):
            if d(textContains="touch firmware").exists() or d(textMatches="(?i).*update.*touch.*").exists():
                logging.info("Dismissing Touch IC Firmware Update popup...")
                if d(text="NO").exists():
                    d(text="NO").click()
                    time.sleep(2)
        
        # 2. General OOBE/Permission dismissals
        if d(text="Allow").exists(): d(text="Allow").click()
        if d(text="CONFIRM").exists(): d(text="CONFIRM").click()

        # 3. Force clean start: Kill potential UI hijackers
        d.press("home")
        d.app_stop("com.android.settings")
        d.app_stop("com.google.android.apps.maps")
        d.app_stop("com.google.android.gms")
        time.sleep(2)

    def reset_device_to_factory_settings(self):
        """Standardized industrial reset: UI-driven (Primary). Tier 2 removed for User Build stability."""
        logging.info("--- Starting Automated Factory Reset (UI Mode) ---")
        
        # 1. Primary Method: Settings UI via Hierarchical Navigation + UIAutomator2
        try:
            logging.info("Tier 1: Triggering via Settings UI (Navigational Approach)...")
            from uiautomator2 import connect
            d = connect()
            
            # Pre-cleaning
            self._clean_and_dismiss_popups(d)
            
            # Re-open Settings (Use direct intent to be more authoritative)
            logging.info("Opening Settings...")
            d.shell("am start -W -a android.settings.SETTINGS")
            time.sleep(2)
            
            # Hierarchical navigation: System -> Reset options -> Erase all data (factory reset) -> Confirm (twice)
            nav_sequence = ["System", "Reset options", "Erase all data (factory reset)", "Erase all data", "Erase all data"]
            for target in nav_sequence:
                logging.info(f"UI Search -> Looking for target: '{target}'")
                
                found = False
                # Manual swipe loop (Max 15 swipes)
                for swipe_attempt in range(15):
                    # Environment check: If we are searching for 'System' but see Google Maps elements,
                    # it means we are likely trapped. Trigger recovery.
                    if target == "System" and swipe_attempt == 3:
                        if d(textContains="Explore").exists() or d(textContains="Contribute").exists():
                            logging.warning("Detected Google Maps hijacking! Re-opening Settings...")
                            d.app_stop("com.google.android.apps.maps")
                            d.shell("am start -W -a android.settings.SETTINGS")
                            time.sleep(2)

                    # For the last two confirmation steps, prioritize BUTTON type
                    if target == "Erase all data":
                        btn = d(textContains=target, className="android.widget.Button")
                    else:
                        btn = d(textContains=target)
                    
                    if btn.exists():
                        logging.info(f"Found target '{target}' (type: Button if confirmation). Clicking...")
                        btn.click()
                        time.sleep(4) # More time for transition/reboot trigger
                        found = True
                        break
                    else:
                        logging.info(f"Target '{target}' not found (Attempt {swipe_attempt+1}/15). Swiping up...")
                        d.swipe_ext("up", scale=0.7)
                        time.sleep(1.5)
                
                if not found:
                    logging.error(f"Navigation failed at: {target}. Screen dump for audit:")
                    # Capture current UI text labels for final debug before failing
                    try:
                        texts = [el.get_text() for el in d(className="android.widget.TextView")]
                        logging.error(f"Visible texts: {texts}")
                    except: pass
                    raise Exception(f"Failed to find navigation target: {target}")

            # Final check for reboot trigger
            logging.info("UI Navigation complete. Monitoring for reboot (30s)...")
            start_monitor = time.time()
            while time.time() - start_monitor < 30:
                try:
                    # If device disconnects, adb will fail
                    subprocess.check_output(["adb", "shell", "getprop", "sys.boot_completed"], timeout=5)
                except:
                    logging.info("Device disconnected. Factory reset successfully triggered.")
                    self._wait_for_oobe_return()
                    return
                time.sleep(5)
            logging.warning("UI navigation finished but device did not reboot within 30s.")
        except Exception as e:
            logging.error(f"Factory Reset failed: {e}")
          
        self._wait_for_oobe_return()

    def _wait_for_oobe_return(self, timeout=120):
        """Blocks until device returns to system/unauthorized mode after reset."""
        logging.info(f"Reset cycling... Waiting up to {timeout}s for OOBE...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                out = subprocess.check_output(["adb", "devices"]).decode()
                if "device" in out or "unauthorized" in out:
                    logging.info("Device successfully returned to OOBE/System.")
                    return True
            except: pass
            time.sleep(5)
        return False

    def _execute_sequence(self, sequence):
        # 1. Reset/Start from scratch (Optional: Only if Home isn't already handled)
        # self.press_key(KEY_NONE, MOD_LMETA) 
        # time.sleep(2)

        def check_adb():
            try:
                out = subprocess.check_output(["adb", "devices"]).decode()
                return "\tdevice" in out
            except: return False

        for step in sequence:
            # Short-circuit if ADB becomes ready mid-sequence
            if check_adb():
                logging.info("ADB detected during sequence. Terminating OOBE clicks early.")
                return True

            logging.info(f"HID Event -> Sending: {step}")
            if step == "TAB":
                self.press_key(KEY_TAB)
                time.sleep(0.6)
            elif step == "ENTER":
                self.press_key(KEY_ENTER)
                time.sleep(2.0)
            elif step == "DOWN":
                self.press_key(KEY_DOWN)
                time.sleep(0.4)
            elif step == "UP":
                self.press_key(KEY_UP)
                time.sleep(0.4)
            elif step == "LEFT":
                self.press_key(KEY_LEFT)
                time.sleep(0.4)
            elif step == "RIGHT":
                self.press_key(KEY_RIGHT)
                time.sleep(0.4)
            elif step == "SETTINGS":
                self.press_key(KEY_I, MOD_LMETA)
                time.sleep(2)
            elif step == "SLEEP_1":
                time.sleep(1.0)
            elif step == "SYS_BACK":
                self.press_back()
                time.sleep(1.0)
            elif step == "SYS_HOME":
                self.press_home()
                time.sleep(1.0)
            elif step == "ESC":
                self.press_key(KEY_ESC)
                time.sleep(0.5)
        
        logging.info("OOBE/Sequence complete.")

def run_oobe_bypass(sku="gms", timeout=600):
    """Wait for device to appear and then run the OOBE bypass + ADB enable sequence with retries."""
    logging.info(f"Waiting for device to appear on USB (timeout={timeout}s, SKU={sku})...")
    start = time.time()
    driver = AOADriver()
    
    def is_adb_ready():
        try:
            import subprocess
            out = subprocess.check_output(["adb", "devices"]).decode()
            return "\tdevice" in out
        except:
            return False

    while time.time() - start < timeout:
        # 1. First priority: Check if ADB is ALREADY ready (authorized/userdebug)
        # If it is, we can skip everything and return success immediately
        if is_adb_ready():
            logging.info("ADB is already ready and authorized. Skipping OOBE/HID sequence.")
            # Even if it's already ready, we ensure developer settings are ON as a precaution
            try:
                subprocess.run(["adb", "shell", "settings", "put", "global", "development_settings_enabled", "1"], capture_output=True)
                subprocess.run(["adb", "shell", "settings", "put", "global", "adb_enabled", "1"], capture_output=True)
            except: pass
            return True

        # 2. If not ready, poll for USB device to start AOA flow
        if driver.find_device():
            logging.info("Device detected! Starting AOA handshake...")
            if driver.switch_to_accessory_mode():
                driver.register_hid(1, KB_REPORT_DESC)
                driver.register_hid(2, CONSUMER_REPORT_DESC)
                
                bypass = OOBEBypass(driver)
                
                # Branching Strategy for GMS (Try SIM path then No-SIM path)
                attempts = [True, False] if sku == "gms" else [True]
                
                for has_sim in attempts:
                    logging.info(f"Attempting OOBE Bypass (SKU: {sku}, SIM: {has_sim})...")
                    # 1. Reset OOBE to start (Multiple Back presses)
                    logging.info("Resetting OOBE state (10x BACK)...")
                    for _ in range(10):
                        bypass.press_back()
                        time.sleep(0.3)
                    time.sleep(5)
                    
                    # 2. Safety ESC to clear any language lists or popups
                    logging.info("Sending safety ESC...")
                    bypass.press_key(KEY_ESC)
                    time.sleep(1)
                    
                    # 3. Run OOBE Sequence
                    if sku == "china":
                        bypass.bypass_china_oobe()
                    else:
                        bypass.bypass_gms_oobe(has_sim=has_sim)
                    
                    logging.info("OOBE Sequence finished. Waiting 5s before enabling ADB...")
                    time.sleep(5)
                    
                    # 3. Try Enable ADB
                    bypass.enable_adb_trimble(sku=sku)
                    
                    # 4. Check Success
                    if is_adb_ready():
                        logging.info("MISSION SUCCESS: ADB is authorized and device is ready!")
                        return True
                    
                    logging.warning(f"Bypass attempt (SIM={has_sim}) failed to enable ADB. Retrying alternative...")
                    time.sleep(2)

                # If both failed in this session, keep polling
                logging.error("All OOBE paths in this session failed. Polling USB again...")
            else:
                logging.warning("Handshake failed, retrying...")
        
        time.sleep(5) # Poll USB every 5s
    
    logging.error("OOBE Bypass failed: Timeout reached.")
    return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_oobe_bypass()
