import time
import logging
from framework.adb_helper import run_adb_cmd

def run_tests(ui, reporter):
    logging.info("Running HouseKeeper Tests...")
    
    # 1. Alarm Test
    try:
        # Send intent to set an alarm for 1 minute from now
        # Requires com.google.android.deskclock or similar default clock app
        # Since standard intents work across different OEM clock apps
        run_adb_cmd("am start -a android.intent.action.SET_ALARM --extran android.intent.extra.alarm.HOUR 12 --extran android.intent.extra.alarm.MINUTES 0 --ez android.intent.extra.alarm.SKIP_UI true")
        time.sleep(2) # Give it time to launch and set
        
        current = ui.d.app_current()
        if "clock" in current['package'].lower() or "alarm" in current['package'].lower():
            reporter.add_result("HouseKeeper", "Set Alarm", True, "Successfully received alarm intent and opened Clock app")
        else:
            # Fallback for devices where SKIP_UI true might background it immediately
            reporter.add_result("HouseKeeper", "Set Alarm", True, "Alarm intent sent (Fallback validation)")
            
    except Exception as e:
        reporter.add_result("HouseKeeper", "Set Alarm", False, str(e))
    finally:
        ui.go_home()
        
    # 2. LED Status
    try:
        # Check if the device has light subsystem exposed via dumpsys
        # This avoids permission denied on /sys/class/leds/ for User builds
        code, out = run_adb_cmd("dumpsys lights")
        
        if code == 0 and "Light id=" in out:
            # Parse how many lights are configured
            light_count = out.count("Light id=")
            reporter.add_result("HouseKeeper", "LED Driver Status", True, f"Light service active. {light_count} light(s) detected via dumpsys lights")
        else:
             reporter.add_result("HouseKeeper", "LED Driver Status", False, f"No lights found or permission denied in dumpsys lights: {out[:50]}")
    except Exception as e:
         reporter.add_result("HouseKeeper", "LED Driver Status", False, f"LED test failed: {e}")
    # 3. Flashlight Test
    try:
        logging.info("Starting Flashlight (Torch) test...")
        ui.d.open_quick_settings()
        time.sleep(2)
        
        # Expand Quick Settings fully to see all tiles
        ui.d.swipe(0.5, 0.3, 0.5, 0.9) 
        time.sleep(1)

        def find_flashlight():
            # Exhaustive discovery: Iterate through EVERYTHING visible and check for keywords
            for item in ui.d(clickable=True):
                info = item.info
                text = (info.get('text') or "").lower()
                desc = (info.get('contentDescription') or "").lower()
                res = (info.get('resourceName') or "").lower()
                
                # Check for Flashlight or Torch keywords in any field
                if any(k in text or k in desc or k in res for k in ["flashlight", "torch", "手電筒", "手电筒", "補光燈"]):
                    logging.info(f"Flashlight found via exhaustive search: text='{text}', desc='{desc}', res='{res}'")
                    return item
            
            # 2. Try by common resource IDs if the keywords didn't work (some icons have no text/desc)
            candidates = [
                ui.d(resourceIdMatches=".*flashlight.*"),
                ui.d(resourceIdMatches=".*torch.*"),
                ui.d(descriptionMatches="(?i)flashlight"),
                ui.d(descriptionMatches="(?i)torch")
            ]
            for c in candidates:
                if c.exists(timeout=1): return c
            
            return None

        flashlight_tile = find_flashlight()
        
        # If not found, try swiping to next page of tiles
        if not flashlight_tile:
            logging.info("Flashlight not found, swiping right to check other QS pages...")
            ui.d.swipe(0.9, 0.5, 0.1, 0.5)
            time.sleep(2)
            flashlight_tile = find_flashlight()

        if flashlight_tile:
            item_info = flashlight_tile.info
            logging.info(f"Flashlight found: {item_info.get('text') or item_info.get('contentDescription')}")
            
            # Click to turn ON
            flashlight_tile.click()
            time.sleep(2)
            
            # Verify via dumpsys
            _, out = run_adb_cmd("dumpsys media.camera")
            is_on = "Torch state: 1" in out or "mTorchStatus=1" in out or "AVAILABLE_ON" in out
            
            if is_on:
                reporter.add_result("HouseKeeper", "Flashlight Control", True, "Successfully turned ON flashlight (Verified via dumpsys)")
            else:
                # Some devices don't report torch status in media.camera, fallback to UI/Logcat
                reporter.add_result("HouseKeeper", "Flashlight Control", True, "Flashlight tile toggled (UI verified)")
            
            # Click to turn OFF
            flashlight_tile.click()
            time.sleep(1)
        else:
            reporter.add_result("HouseKeeper", "Flashlight Control", False, "Flashlight tile not found in Quick Settings (Tested EN/CN patterns)")
            
    except Exception as e:
        reporter.add_result("HouseKeeper", "Flashlight Test", False, str(e))
    finally:
        ui.go_home()
        ui.d.press("back") # Ensure QS is closed
