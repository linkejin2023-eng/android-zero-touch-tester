import uiautomator2 as u2
import logging
import time

class UIHelper:
    def __init__(self, serial=None):
        try:
            logging.info("Connecting to uiautomator2...")
            self.d = u2.connect(serial) # if None, connects to local device
            # This triggers the automatic installation of uiautomator apks if missing
            self.d.app_info("com.android.settings") 
            logging.info("UIAutomator2 connected successfully.")
        except Exception as e:
            logging.error(f"Failed to connect UIAutomator2: {e}")
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
