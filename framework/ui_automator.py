import uiautomator2 as u2
import logging
import time

class UIHelper:
    def __init__(self, serial: str = None, retries=3):
        import subprocess
        self.serial = serial
        self.d = None
        
        for attempt in range(retries):
            try:
                # Pre-emptive strike: Clear potential overlays via ADB
                logging.info(f"UIAutomator2 connection attempt {attempt + 1}/{retries}...")
                adb_prefix = f"adb -s {serial}" if serial else "adb"
                subprocess.run(f"{adb_prefix} shell input keyevent 3", shell=True, capture_output=True)
                time.sleep(2)
                
                self.d = u2.connect(serial)
                # Verify connection quality
                self.d.app_info("com.android.settings")
                logging.info("UIAutomator2 connected successfully.")
                return
            except Exception as e:
                logging.warning(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < retries - 1:
                    wait_time = (attempt + 1) * 5
                    logging.info(f"Waiting {wait_time}s before retrying...")
                    time.sleep(wait_time)
                else:
                    logging.error("All UIAutomator2 connection attempts failed.")
                    raise e
            
    def launch_app(self, package_name: str):
        logging.info(f"Launching app: {package_name}")
        self.d.app_start(package_name, stop=True)
        time.sleep(2)
        
    def click_text(self, text: str, timeout: int = 5) -> bool:
        logging.info(f"Looking for text to click: '{text}'")
        if self.d(text=text).wait(timeout=timeout):
            self.d(text=text).click()
            return True
        return False
        
    def click_desc(self, desc: str, timeout: int = 5) -> bool:
        logging.info(f"Looking for content-desc to click: '{desc}'")
        if self.d(description=desc).wait(timeout=timeout):
            self.d(description=desc).click()
            return True
        return False

    def scroll_to_text(self, text: str):
        self.d(scrollable=True).scroll.to(text=text)

    def go_home(self):
        self.d.press("home")

    def dismiss_china_settings_popup(self) -> bool:
        """Looks for the China SKU 'User Notice' popup (Simplified Chinese '确定') and clicks it."""
        logging.info("Checking for China SKU 'User Notice' (确定) popup...")
        # Use textMatches for flexibility or direct text
        btn = self.d(text="确定")
        if btn.exists(timeout=3):
            logging.info("Found China SKU popup, clicking '确定'...")
            btn.click()
            time.sleep(1)
            return True
        logging.info("No China SKU popup detected.")
        return False

    def ensure_settings_ready(self):
        """Forces settings to open and dismisses any initialization popups (China SKU specific)."""
        logging.info("Ensuring Settings app is ready and popups are dismissed...")
        self.launch_app("com.android.settings")
        time.sleep(2)
        self.dismiss_china_settings_popup()
        # Return to home to keep environment clean
        self.go_home()
        time.sleep(1)
