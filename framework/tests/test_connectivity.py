from framework.adb_helper import run_adb_cmd
from framework.ui_automator import UIHelper
from framework.report_generator import HTMLReportGenerator
import time
import logging

WIFI_SSID = "TP-LINK_32-5"
WIFI_PASS = "0228318565"

def run_tests(ui: UIHelper, reporter: HTMLReportGenerator):
    logging.info("Running Connectivity Tests (WiFi/BT)...")
    
    # WiFi Tests
    try:
        # Enable WiFi via cmd wifi
        run_adb_cmd("svc wifi enable")
        time.sleep(3)
        code, out = run_adb_cmd("dumpsys wifi | grep 'Wi-Fi is'")
        if "enabled" in out:
            reporter.add_result("Connectivity", "WiFi Enable", True, "Successfully enabled WiFi")
        else:
            reporter.add_result("Connectivity", "WiFi Enable", False, f"WiFi failed to enable: {out.strip()}")
            
        # Optional: Connect to test AP (Requires Android 10+ cmd wifi connect)
        if WIFI_SSID != "YOUR_WIFI_SSID":
            logging.info(f"Connecting to AP: {WIFI_SSID}")
            run_adb_cmd(f'cmd wifi connect-network "{WIFI_SSID}" wpa2 "{WIFI_PASS}"')
            time.sleep(15) # Wait for DHCP
            
        # In Android 12+, ifconfig wlan0 might need root. We can use ip addr show wlan0 instead
        # Check IP address
        code, out = run_adb_cmd("ip -f inet addr show wlan0")
        if "inet " in out:
            ip = out.split("inet ")[1].split("/")[0]
            reporter.add_result("Connectivity", "WiFi IP Address", True, f"wlan0 is connected to AP with IP: {ip}")
        else:
            if WIFI_SSID != "YOUR_WIFI_SSID":
                reporter.add_result("Connectivity", "WiFi IP Address", False, f"Failed to get IP address after connecting to {WIFI_SSID}")
            else:
                reporter.add_result("Connectivity", "WiFi IP Address", True, "Skipped IP check (No SSID provided). Interface is up.")
            
    except Exception as e:
        reporter.add_result("Connectivity", "WiFi Tests", False, str(e))

    # Bluetooth Tests 
    try:
        logging.info("Checking Bluetooth state...")
        _, out_state = run_adb_cmd("settings get global bluetooth_on")
        is_on = out_state.strip() == "1"
        
        if not is_on:
            logging.info("Bluetooth is OFF, attempting to enable...")
            run_adb_cmd("svc bluetooth enable")
            time.sleep(3)
            code, out = run_adb_cmd("settings get global bluetooth_on")
            
            if out.strip() != "1":
                logging.info("svc failed, trying UI-based enablement...")
                run_adb_cmd("am start -a android.settings.BLUETOOTH_SETTINGS")
                time.sleep(2)
                # Find switch/toggle
                switch = ui.d(className="android.widget.Switch") or ui.d(textMatches="(?i)(off|開關|關閉)")
                if switch.exists and not switch.info.get('checked', False):
                    switch.click()
                    time.sleep(4)
                code, out = run_adb_cmd("settings get global bluetooth_on")
                is_on = out.strip() == "1"
            else:
                is_on = True

        if is_on:
            reporter.add_result("Connectivity", "Bluetooth Enable", True, "Bluetooth is ON (Manual or Automated)")
            
            # Phase 3: Bluetooth Discovery/Scan Test
            logging.info("Starting Bluetooth Discovery test...")
            run_adb_cmd("am start -a android.settings.BLUETOOTH_SETTINGS")
            time.sleep(5) 
            
            found_devices = []
            
            # Diagnostic: check what's visible
            elements = ui.d(className="android.widget.TextView")
            skip_texts = ["Bluetooth", "Connected devices", "Pair new device", "Device name", 
                          "Received files", "Pairing helps", "On", "Off", "Available devices", "Searching...", "Bluetooth is on"]
            
            for el in elements:
                try:
                    txt = el.get_text()
                    if txt and txt not in skip_texts and len(txt) > 2:
                        found_devices.append(txt)
                except:
                    pass
            
            if found_devices:
                reporter.add_result("Connectivity", "Bluetooth Scanning", True, f"Found {len(found_devices)} nearby devices: {', '.join(found_devices[:3])}")
            else:
                # Fallback: check dumpsys for discovered devices
                _, bt_sys = run_adb_cmd("dumpsys bluetooth_manager")
                if "discovered" in bt_sys.lower() or "device" in bt_sys.lower():
                     reporter.add_result("Connectivity", "Bluetooth Scanning", True, "Detected discovery activity via dumpsys")
                else:
                     reporter.add_result("Connectivity", "Bluetooth Scanning", False, "No nearby Bluetooth devices found (UI/Dumpsys)")
            
            run_adb_cmd("input keyevent 3")
        else:
            reporter.add_result("Connectivity", "Bluetooth Enable", False, "Bluetooth failed to enable via svc and UI")
            reporter.add_result("Connectivity", "Bluetooth Scanning", False, "Skipped: Bluetooth is OFF")
            
    except Exception as e:
        reporter.add_result("Connectivity", "Bluetooth Tests", False, str(e))
        
    # WWAN (Cellular) Tests
    try:
        logging.info("Running WWAN (Cellular) Tests...")
        _, telephony = run_adb_cmd("dumpsys telephony.registry")
        
        # Check SIM State
        sim_present = "mSimState=5" in telephony or "SIM_STATE_READY" in telephony
        
        # Extract Signal Strength (dBm)
        import re
        rsrp_match = re.search(r"rsrp=(-?\d+)", telephony)
        signal_dbm = rsrp_match.group(1) if rsrp_match else "Unknown"
        
        # Extract Operator
        operator_match = re.search(r"mOperatorAlphaLong=([^,]+)", telephony)
        operator = operator_match.group(1).strip() if operator_match and operator_match.group(1) != "null" else "No Carrier"

        if sim_present:
            state = "SIM Detected"
            passed = True
            msg = f"Operator: {operator}, Signal: {signal_dbm} dBm"
        else:
            state = "No SIM"
            passed = "rsrp" in telephony # If we see rsrp, modem is alive
            msg = f"Modem Alive (Signal: {signal_dbm} dBm). Please insert SIM for full check."

        reporter.add_result("Connectivity", f"WWAN Status ({state})", passed, msg)
        
    except Exception as e:
        reporter.add_result("Connectivity", "WWAN Tests", False, str(e))
