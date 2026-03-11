from aoa_driver import AOADriver, KB_REPORT_DESC
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
        self.driver.send_hid_event(self.hid_kb_id, press_report)
        time.sleep(duration)
        
        release_report = bytearray([0, 0, 0, 0, 0, 0, 0, 0])
        self.driver.send_hid_event(self.hid_kb_id, release_report)
        time.sleep(duration)

    def press_home(self, duration=0.05):
        """Sends a Consumer Page Home event (0x0223) - HID ID 2."""
        # 16-bit Usage ID in Little-Endian: 0x0223 -> [0x23, 0x02]
        press_report = bytearray([0x23, 0x02])
        self.driver.send_hid_event(self.hid_consumer_id, press_report)
        time.sleep(duration)
        
        # Release (Send 0x0000)
        release_report = bytearray([0x00, 0x00])
        self.driver.send_hid_event(self.hid_consumer_id, release_report)
        time.sleep(duration)

    def press_back(self, duration=0.05):
        """Sends a Consumer Page Back event (0x0224) - HID ID 2."""
        # 16-bit Usage ID in Little-Endian: 0x0224 -> [0x24, 0x02]
        press_report = bytearray([0x24, 0x02])
        self.driver.send_hid_event(self.hid_consumer_id, press_report)
        time.sleep(duration)
        
        release_report = bytearray([0x00, 0x00])
        self.driver.send_hid_event(self.hid_consumer_id, release_report)
        time.sleep(duration)

    def enable_adb_trimble(self):
        """Automates the full ADB enablement sequence including re-enumeration handling."""
        logging.info("Starting ADB Enablement sequence (Trimble T70)...")
        
        # 1. Enter Settings (Win+I)
        self.press_key(KEY_I, MOD_LMETA)
        time.sleep(1)

        # 2. Sequence based on user recording to reach Build Number and Tap 7 times
        # Sequence: TABx17 -> ENTER -> TABx5 -> DOWNx5 -> TABx3 -> DOWNx7 -> ENTER -> MULTI_ENTER
        # NOTE: Using loops to keep it readable
        for _ in range(17): self.press_key(KEY_TAB)
        for _ in range(17): self.press_key(KEY_DOWN) # Extra scrolls to be safe
        self.press_key(KEY_ENTER)
        time.sleep(1)
        
        for _ in range(5): self.press_key(KEY_TAB)
        for _ in range(5): self.press_key(KEY_DOWN)
        self.press_key(KEY_TAB, duration=0.1) # Mixed navigation
        
        # Open Developer Options / Find Build Number
        # (Based on the user response, we assume the provided sequence reaches Build Number)
        sequence = ["TAB"]*17 + ["ENTER"] + ["TAB"]*5 + ["DOWN"]*5 + ["TAB"]*3 + ["DOWN"]*7 + ["ENTER"] + ["MULTI_ENTER"]
        # Wait, the user provided a very specific combined sequence. Let's use it exactly.
        
        hybrid_seq = [
            "TAB", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", 
            "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "ENTER", # Enters About Phone?
            "TAB", "TAB", "TAB", "TAB", "TAB", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", 
            "TAB", "TAB", "TAB", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "ENTER", # Build number?
            "MULTI_ENTER", "SYS_BACK", "UP", "ENTER", # Dev options
            "TAB", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "ENTER", # Toggle ADB
            "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB",
            "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "ENTER", "TAB", "TAB", "ENTER"
        ]

        for cmd in hybrid_seq:
            try:
                if cmd == "TAB": self.press_key(KEY_TAB)
                elif cmd == "ENTER": 
                    self.press_key(KEY_ENTER)
                    time.sleep(2) # Give UI time to react
                elif cmd == "DOWN": self.press_key(KEY_DOWN)
                elif cmd == "UP": self.press_key(KEY_UP)
                elif cmd == "MULTI_ENTER": 
                    for _ in range(7):
                        self.press_key(KEY_ENTER)
                        time.sleep(0.1)
                elif cmd == "SYS_BACK": self.press_back()
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
        if self.driver.switch_to_accessory_mode():
            self.driver.register_hid(1, KB_REPORT_DESC)
            from aoa_driver import CONSUMER_REPORT_DESC
            self.driver.register_hid(2, CONSUMER_REPORT_DESC)
            
            logging.info("Re-connected! Sending final 'Allow USB Debugging' sequence...")
            # After re-enumeration, the 'Allow USB Debugging' dialog is visible
            # User said: enter > tab > tab > enter(allow button)
            self.press_key(KEY_ENTER)
            time.sleep(1)
            self.press_key(KEY_TAB)
            self.press_key(KEY_TAB)
            self.press_key(KEY_ENTER)
            logging.info("ADB Enablement Complete.")
        else:
            logging.error("Failed to reconnect after ADB toggle.")

    def type_string(self, text):
        """Simple string typer (lowercase only for now)."""
        for char in text.lower():
            if 'a' <= char <= 'z':
                keycode = ord(char) - ord('a') + 4
                self.press_key(keycode)
            elif char == ' ':
                self.press_key(KEY_SPACE)
            time.sleep(0.05)

    def bypass_trimble_oobe(self):
        logging.info("Starting OOBE Bypass sequence for Trimble T70 (Android 15)...")
        
        # Final hybrid sequence from user
        sequence = [
            "TAB", "TAB", "TAB", "ENTER", 
            "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "ENTER", 
            "TAB", "TAB", "ENTER", 
            "TAB", "TAB", "TAB", "TAB", "ENTER", 
            "TAB", "TAB", "TAB", "TAB", "ENTER", 
            "TAB", "TAB", "ENTER", 
            "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "ENTER"
        ]
        
        # 1. Home / Reset to ensure starting from scratch
        self.press_key(KEY_NONE, MOD_LMETA) 
        time.sleep(2)

        for step in sequence:
            if step == "TAB":
                self.press_key(KEY_TAB)
                time.sleep(0.4)
            elif step == "ENTER":
                self.press_key(KEY_ENTER)
                time.sleep(2.0) # 2s delay after Enter
            elif step == "DOWN":
                self.press_key(KEY_DOWN)
                time.sleep(0.15)
        
        logging.info("OOBE Sequence complete. Please check if device reached Home screen.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    driver = AOADriver()
    if driver.find_android_device(vid=0x099E, pid=0x02B1):
        if driver.switch_to_accessory_mode():
            driver.register_hid(1, KB_REPORT_DESC)
            bypass = OOBEBypass(driver)
            bypass.bypass_trimble_oobe()
