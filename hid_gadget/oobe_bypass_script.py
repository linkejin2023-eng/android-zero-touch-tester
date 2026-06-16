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
    def __init__(self, driver, serial=None):
        self.driver = driver
        self.serial = serial
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
        hybrid_seq = ["SETTINGS"]
        
        if sku == "china":
            hybrid_seq.extend(["TAB", "TAB", "ENTER"])
            
        adb_toggle_downs = (["DOWN"] * 12 + ["UP"]) if sku == "china" else ["DOWN"] * 7
        final_toggle_downs = ["DOWN"] * (12 if sku == "china" else 14)
        
        hybrid_seq.extend([
            "TAB", "TAB", "TAB", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", 
            "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "ENTER", 
            "TAB", "TAB", "TAB", # 3 TABS to reach the list
            "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", 
            "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", # 15 DOWNS to hit bottom (Build Number)
            "ENTER", # Trigger/Focus Build number
            "MULTI_ENTER", "SYS_BACK", "UP", "ENTER", "TAB"
        ] + adb_toggle_downs + [
            "ENTER", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB"
        ] + final_toggle_downs + [
            "ENTER", "TAB", "TAB", "ENTER"
        ])

        for cmd in hybrid_seq:
            try:
                if cmd == "SETTINGS":
                    self.press_key(KEY_I, MOD_LMETA)
                    time.sleep(2.0)
                elif cmd == "TAB": 
                    self.press_key(KEY_TAB)
                    time.sleep(1.0)
                elif cmd == "ENTER": 
                    self.press_key(KEY_ENTER)
                    time.sleep(2)
                elif cmd == "DOWN": 
                    self.press_key(KEY_DOWN)
                    time.sleep(0.5) # 提高延遲以適應 UI 渲染
                elif cmd == "UP": 
                    self.press_key(KEY_UP)
                    time.sleep(0.5) # 提高延遲以適應 UI 渲染
                elif cmd == "MULTI_ENTER": 
                    for _ in range(7):
                        self.press_key(KEY_ENTER)
                        time.sleep(0.1)
                    time.sleep(1.0) # 等待 Toast 提示穩定
                elif cmd == "SYS_BACK": 
                    self.press_back()
                    time.sleep(1.5) # 給予足夠轉場時間
                elif cmd == "SYS_HOME": 
                    self.press_home()
                    time.sleep(1.5) # 給予足夠轉場時間
                logging.info(f"HID Event Sent: {cmd}")
            except Exception as e:
                if "No such device" in str(e) or "Pipe error" in str(e):
                    logging.warning("Device disconnected (likely PID change). Starting reconnection...")
                    break
        
        # 3. Handle Re-enumeration (PID change)
        time.sleep(5)
        logging.info("Attempting to reconnect after ADB toggle...")
        if self.driver.find_device(serial=self.serial):
            if self.driver.switch_to_accessory_mode():
                self.driver.register_hid(1, KB_REPORT_DESC)
                self.driver.register_hid(2, CONSUMER_REPORT_DESC)
                
                logging.info("Re-connected! Sending final 'Allow USB Debugging' sequence...")
                
                def is_adb_authorized():
                    try:
                        import subprocess
                        out = subprocess.check_output(["adb", "devices"]).decode()
                        check_sn = self.serial if self.serial else ""
                        if check_sn:
                            return f"{check_sn}\tdevice" in out
                        return "\tdevice" in out
                    except: return False

                for attempt in range(3):
                    if is_adb_authorized():
                        logging.info("ADB already authorized! Skipping further HID inputs.")
                        break
                    logging.info(f"Authorization attempt {attempt + 1}...")
                    self.press_key(KEY_ENTER) 
                    time.sleep(0.5)
                    self.press_key(KEY_TAB)
                    self.press_key(KEY_TAB)
                    self.press_key(KEY_ENTER)
                    time.sleep(5) # 增加等待時間讓 ADB 狀態生效

                if is_adb_authorized():
                    logging.info("MISSION ACCOMPLISHED: ADB authorized successfully!")
                    return True
                
                logging.info("ADB Enablement Step Finished (Authorization pending or failed).")
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

        # PIN Screen + Confirm dialog + Google Services
        sequence.extend([
            "SYS_BACK", "TAB", "ENTER",      # PIN Screen Skip (BACK to hide keyboard, TAB to focus Skip)
            "SLEEP_1", "TAB", "TAB", "ENTER", # Skip anyway dialog
            "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", "TAB", 
            "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "DOWN", "ENTER" # Google Services (6x DOWN to hit Accept)
        ])
        
        return self._execute_sequence(sequence)

    def bypass_china_oobe(self):
        logging.info("Starting China SKU OOBE Bypass sequence for Trimble T70...")
        
        # Sequence provided by user for China SKU
        sequence = [
            "TAB", "TAB", "ENTER", # Welcome screen / Language?
            "TAB", "TAB", "TAB", "TAB", "TAB", "ENTER" # China specific Skip flow
        ]
        return self._execute_sequence(sequence)

    def reset_device_to_factory_settings(self):
        """Executes the recorded HID sequence to perform a Factory Reset."""
        logging.info("Starting Factory Reset sequence via HID (including Wake-up logic)...")
        
        # 1. Aggressive Wake up & Keyguard Dismiss
        try:
            import subprocess
            # Try ADB wakeup first
            logging.info("Attempting to wake up device and dismiss keyguard via ADB...")
            subprocess.run(["adb", "shell", "input", "keyevent", "KEYCODE_WAKEUP"], capture_output=True)
            subprocess.run(["adb", "shell", "wm", "dismiss-keyguard"], capture_output=True)
            time.sleep(1)
        except:
            pass

        # 2. HID Fallback Wake up (Send ESC and SPACE to wake screen + dismiss swipe lock)
        logging.info("Sending HID Wake-up/Unlock signals (ESC, SPACE, HOME)...")
        self.press_key(KEY_ESC)
        time.sleep(0.5)
        self.press_key(KEY_SPACE)
        time.sleep(0.5)
        self.press_home() 
        time.sleep(1.5)
        
        # 3. Pre-cleanup Settings (Force reset state)
        try:
            from framework.adb_helper import run_adb_cmd
            logging.info("Ensuring Settings app is in a fresh state...")
            run_adb_cmd("am force-stop com.android.settings")
            time.sleep(1.0)
            # Use --clear-task to force back to the root menu
            run_adb_cmd("am start -a android.settings.SETTINGS --clear-task")
            time.sleep(3.0) # Wait for settings to load
        except Exception as e:
            logging.warning(f"Failed to pre-clean settings via ADB: {e}")

        # 2. Recorded Sequence
        # If 'am start' worked, we are in Settings. 
        # If it didn't, 'SETTINGS' (Win+I) is our fallback.
        sequence = ["SETTINGS", "TAB", "SLEEP_1"] # TAB for focus + delay
        sequence.extend(["DOWN"] * 27)
        sequence.extend(["UP", "ENTER"])
        sequence.extend(["DOWN"] * 17)
        sequence.extend(["ENTER"])
        sequence.extend(["DOWN"] * 13)
        sequence.extend(["ENTER"])
        sequence.extend(["TAB", "TAB", "TAB", "ENTER", "TAB", "ENTER"])
        
        self._execute_sequence(sequence)
        logging.info("Factory Reset HID sequence execution finished of course.")

    def _execute_sequence(self, sequence):
        # 1. Reset/Start from scratch (Optional: Only if Home isn't already handled)
        # self.press_key(KEY_NONE, MOD_LMETA) 
        # time.sleep(2)

        for step in sequence:
            success = True
            logging.info(f"HID Event -> Sending: {step}")
            if step == "TAB":
                success = self.press_key(KEY_TAB)
                time.sleep(1.0) # 拉長 TAB 間隔確保 UI 焦點穩定
            elif step == "ENTER":
                success = self.press_key(KEY_ENTER)
                time.sleep(2.0)
            elif step == "DOWN":
                success = self.press_key(KEY_DOWN)
                time.sleep(0.4)
            elif step == "UP":
                success = self.press_key(KEY_UP)
                time.sleep(0.4)
            elif step == "LEFT":
                success = self.press_key(KEY_LEFT)
                time.sleep(0.4)
            elif step == "RIGHT":
                success = self.press_key(KEY_RIGHT)
                time.sleep(0.4)
            elif step == "SETTINGS":
                success = self.press_key(KEY_I, MOD_LMETA)
                time.sleep(2)
            elif step == "SLEEP_1":
                time.sleep(1.0)
            elif step == "SYS_BACK":
                success = self.press_back()
                time.sleep(1.0)
            elif step == "SYS_HOME":
                success = self.press_home()
                time.sleep(1.0)
            elif step == "ESC":
                success = self.press_key(KEY_ESC)
                time.sleep(0.5)
            
            if not success:
                logging.error(f"HID sequence execution aborted at step: {step}")
                return False
        
        logging.info("OOBE/Sequence complete.")
        return True

def run_oobe_bypass(sku="gms", serial=None, timeout=600):
    """Wait for device to appear and then run the OOBE bypass + ADB enable sequence with retries."""
    logging.info(f"Waiting for device to appear on USB (timeout={timeout}s, SKU={sku})...")
    start = time.time()
    driver = AOADriver()
    from framework import adb_helper
    
    def is_adb_ready():
        try:
            res = adb_helper.run_local_adb(["devices"])
            # 使用函數參數中的 serial，若無則回退到全域
            check_sn = serial if serial else adb_helper.GLOBAL_SERIAL
            if check_sn:
                return f"{check_sn}\tdevice" in res.stdout
            return "\tdevice" in res.stdout
        except: return False

    # 確保有目標序號
    target_serial = serial if serial else adb_helper.GLOBAL_SERIAL

    while time.time() - start < timeout:
        if is_adb_ready():
            # 檢查是否真的進入桌面，而非只是 ADB 通了 (針對 China SKU OOBE 攔截問題)
            _, out = adb_helper.run_adb_cmd("dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'")
            if "Launcher" in out or "TabActivity" in out:
                logging.info("ADB detected & Launcher is active. Skipping HID.")
                return True
            else:
                logging.info("ADB detected but OOBE still active. Attempting ADB-based bypass...")
                adb_helper.run_adb_cmd("settings put global device_provisioned 1")
                adb_helper.run_adb_cmd("settings put secure user_setup_complete 1")
                if sku == "china":
                    adb_helper.run_adb_cmd("pm disable com.pega.eulacn")
                adb_helper.run_adb_cmd("am start -c android.intent.category.HOME -a android.intent.action.MAIN")
                time.sleep(2)
                # 再次檢查是否成功跳轉
                _, out_after = adb_helper.run_adb_cmd("dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'")
                if "Launcher" in out_after:
                    logging.info("ADB-based bypass successful.")
                    return True
                logging.warning("ADB-based bypass failed to reach Launcher, proceeding with HID sequence...")

        if driver.find_device(serial=target_serial):
            # 如果是自動鎖定序號，回寫到全域
            if not target_serial:
                target_serial = driver.target_serial
                adb_helper.GLOBAL_SERIAL = target_serial

            logging.info(f"Stage 1: Device {target_serial} locked. Initiating AOA...")
            if driver.switch_to_accessory_mode():
                driver.register_hid(1, KB_REPORT_DESC)
                driver.register_hid(2, CONSUMER_REPORT_DESC)
                
                bypass = OOBEBypass(driver, serial=target_serial)
                
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
                    
                    # 3. Try Enable ADB (Capture return value)
                    if bypass.enable_adb_trimble(sku=sku):
                        logging.info("MISSION SUCCESS: ADB is authorized via enable_adb_trimble!")
                        return True
                    
                    # 4. Final safety Check
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
