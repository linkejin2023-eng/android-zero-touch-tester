import time
import logging
from framework.adb_helper import run_adb_cmd

def run_tests(ui, reporter):
    logging.info("Running Touchscreen Tests...")

    # 1. Swipe Test
    try:
        # Get screen size to calculate swipe coordinates
        info = ui.d.info
        width = info.get('displayWidth')
        height = info.get('displayHeight')
        
        if width and height:
            # Swipe up (from bottom to top)
            ui.d.swipe(width/2, height*0.8, width/2, height*0.2, 0.5)
            time.sleep(1)
            # Swipe down
            ui.d.swipe(width/2, height*0.2, width/2, height*0.8, 0.5)
            time.sleep(1)
            # Swipe left
            ui.d.swipe(width*0.8, height/2, width*0.2, height/2, 0.5)
            time.sleep(1)
            # Swipe right
            ui.d.swipe(width*0.2, height/2, width*0.8, height/2, 0.5)
            time.sleep(1)
            
            reporter.add_result("Touchscreen", "Drag and Drop (Swipe)", True, "Successfully sent swipe commands in all 4 directions")
        else:
            reporter.add_result("Touchscreen", "Drag and Drop (Swipe)", False, "Failed to get display dimensions for swipe")
    except Exception as e:
        reporter.add_result("Touchscreen", "Drag and Drop (Swipe)", False, f"Swipe test failed: {e}")

    # 2. Touch Response Test (Driver Level)
    # We check if dumpsys input lists touchscreen devices
    try:
        code, out = run_adb_cmd("dumpsys input")
        if "Touch" in out or "touch" in out.lower():
            # Basic validation that touch event framework is alive
            reporter.add_result("Touchscreen", "Touchscreen Response", True, "Input framework successfully lists Touch devices")
        else:
             reporter.add_result("Touchscreen", "Touchscreen Response", False, "No Touch devices found in dumpsys input")
    except Exception as e:
        reporter.add_result("Touchscreen", "Touchscreen Response", False, f"dumpsys input check failed: {e}")
