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
KEY_F1 = 0x3a
# ...
KEY_RIGHT = 0x4f
KEY_LEFT = 0x50
KEY_DOWN = 0x51
KEY_UP = 0x52

# Modifiers
MOD_LCTRL = 0x01
MOD_LSHIFT = 0x02
MOD_LALT = 0x04
MOD_LMETA = 0x08

class OOBEBypass:
    def __init__(self, driver):
        self.driver = driver
        self.hid_id = 1

    def press_key(self, keycode, modifier=KEY_NONE, duration=0.05):
        """Sends a key press and release event."""
        # Report format: [modifier, reserved, key1, key2, key3, key4, key5, key6]
        press_report = bytearray([modifier, 0, keycode, 0, 0, 0, 0, 0])
        self.driver.send_hid_event(self.hid_id, press_report)
        time.sleep(duration)
        
        release_report = bytearray([0, 0, 0, 0, 0, 0, 0, 0])
        self.driver.send_hid_event(self.hid_id, release_report)
        time.sleep(duration)

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
