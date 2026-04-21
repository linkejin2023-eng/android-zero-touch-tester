import uiautomator2 as u2
import logging
import time

class UIHelper:
    def __init__(self, serial=None, retries=3):
        import subprocess
        self.d = None
        
        for attempt in range(retries):
            try:
                # Pre-emptive strike: Clear potential overlays via ADB
                logging.info(f"UIAutomator2 connection attempt {attempt + 1}/{retries}...")
                subprocess.run(["adb", "shell", "input", "keyevent", "3"], capture_output=True) # KEYCODE_HOME
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
