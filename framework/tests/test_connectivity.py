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
        run_adb_cmd("svc bluetooth enable")
        time.sleep(3)
        # Using service check since dumpsys bluetooth can be messy
        code, out = run_adb_cmd("settings get global bluetooth_on")
        if out.strip() == "1":
            reporter.add_result("Connectivity", "Bluetooth Enable", True, "Successfully enabled Bluetooth")
        else:
            reporter.add_result("Connectivity", "Bluetooth Enable", False, "Bluetooth failed to enable")
    except Exception as e:
        reporter.add_result("Connectivity", "Bluetooth Tests", False, str(e))
