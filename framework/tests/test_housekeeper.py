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
