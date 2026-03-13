try:
    from .aoa_driver import AOADriver, KB_REPORT_DESC, CONSUMER_REPORT_DESC
except (ImportError, ValueError):
    from aoa_driver import AOADriver, KB_REPORT_DESC, CONSUMER_REPORT_DESC
import time
import logging

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
                elif cmd == "SYS_HOME": self.press_home()
                
                logging.info(f"Executed: {cmd}")
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
                        logging.info("ADB already authorized! Skipping further HID inputs.")
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

    def bypass_gms_oobe(self):
        logging.info("Starting GMS OOBE Bypass sequence for Trimble T70 (Android 15)...")
        
        # Optimized sequence for GMS stability
        sequence = [
            "TAB", "TAB", "TAB", "ENTER", # Welcome screen
            "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "ENTER", # Wi-Fi Skip
            "TAB", "TAB", "ENTER", # Offline setup confirmation
            "TAB", "TAB", "TAB", "TAB", "ENTER", # Date & Time page
            "SYS_BACK", "TAB", "ENTER", # PIN Screen (Back to close keyboard, Tab to Skip button, Enter)
            "TAB", "TAB", "ENTER", # Skip anyway confirmation dialog
            "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "ENTER" # Google Services
        ]
        self._execute_sequence(sequence)

    def bypass_china_oobe(self):
        logging.info("Starting China SKU OOBE Bypass sequence for Trimble T70...")
        
        # Sequence provided by user for China SKU
        sequence = [
            "TAB", "TAB", "ENTER", # Welcome screen / Language?
            "TAB", "TAB", "TAB", "TAB", "TAB", "ENTER" # China specific Skip flow
        ]
        self._execute_sequence(sequence)

    def _execute_sequence(self, sequence):
        # 1. Home / Reset to ensure starting from scratch
        self.press_key(KEY_NONE, MOD_LMETA) 
        time.sleep(2)

        for step in sequence:
            if step == "TAB":
                self.press_key(KEY_TAB)
                time.sleep(0.8)
            elif step == "ENTER":
                self.press_key(KEY_ENTER)
                time.sleep(2.5)
            elif step == "DOWN":
                self.press_key(KEY_DOWN)
                time.sleep(0.8)
            elif step == "SYS_BACK":
                self.press_back()
                time.sleep(1.0)
        
        logging.info("OOBE Sequence complete.")

def run_oobe_bypass(sku="gms", timeout=300):
    """Wait for device to appear and then run the OOBE bypass + ADB enable sequence."""
    logging.info(f"Waiting for device to appear on USB (timeout={timeout}s, SKU={sku})...")
    start = time.time()
    driver = AOADriver()
    
    while time.time() - start < timeout:
        if driver.find_device():
            logging.info("Device detected! Starting AOA handshake...")
            if driver.switch_to_accessory_mode():
                driver.register_hid(1, KB_REPORT_DESC)
                driver.register_hid(2, CONSUMER_REPORT_DESC)
                
                bypass = OOBEBypass(driver)
                logging.info(f"Starting OOBE Bypass for SKU: {sku}...")
                if sku == "china":
                    bypass.bypass_china_oobe()
                else:
                    bypass.bypass_gms_oobe()
                
                logging.info("Waiting 5s for system to stabilize...")
                time.sleep(5)
                
                logging.info("Starting ADB Enablement...")
                bypass.enable_adb_trimble(sku=sku)
                return True
            else:
                logging.warning("Handshake failed, retrying...")
        
        time.sleep(5) # Poll USB every 5s
    
    logging.error("OOBE Bypass failed: Device did not appear or handshake failed.")
    return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_oobe_bypass()
