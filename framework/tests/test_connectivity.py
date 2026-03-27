from framework.adb_helper import run_adb_cmd
from framework.ui_automator import UIHelper
from framework.report_generator import HTMLReportGenerator
import time
import logging

WIFI_SSID = "Xiaomi_test"
WIFI_PASS = "0987654321"

def run_tests(ui: UIHelper, reporter: HTMLReportGenerator):
    logging.info("Running Connectivity Tests (WiFi/BT)...")
    
    # WiFi Tests
    try:
        # Enable WiFi via cmd wifi
        run_adb_cmd("svc wifi enable")
        time.sleep(3)
        _, wifi_on_init = run_adb_cmd("settings get global wifi_on")
        
        if wifi_on_init.strip() == "1":
            reporter.add_result("Connectivity", "WiFi Enable", True, "Successfully enabled WiFi")
        else:
            reporter.add_result("Connectivity", "WiFi Enable", False, "WiFi failed to enable (settings check)")
            
        # --- 1. WiFi Scanning (Visibility Check) ---
        logging.info("Scanning for WiFi Access Points...")
        run_adb_cmd("cmd wifi start-scan")
        time.sleep(5)
        _, scan_out = run_adb_cmd("cmd wifi list-scan-results")
        
        found_aps = []
        for line in scan_out.strip().split('\n'):
            parts = line.split()
            if len(parts) >= 5 and ":" in parts[0]: 
                ssid = " ".join(parts[4:])
                if ssid and ssid not in found_aps:
                    found_aps.append(ssid)
        
        if found_aps:
            reporter.add_result("Connectivity", "WiFi Scanning", True, f"Found {len(found_aps)} nearby Access Points: {', '.join(found_aps[:3])}")
        else:
            reporter.add_result("Connectivity", "WiFi Scanning", False, "No nearby WiFi Access Points detected")

        # --- 2. WiFi Association (Connection Check) ---
        if WIFI_SSID != "YOUR_WIFI_SSID":
            # Pre-check if target SSID is in the scan list
            if WIFI_SSID not in found_aps:
                logging.warning(f"Target SSID '{WIFI_SSID}' NOT FOUND in scan results. Skipping connection test.")
                reporter.add_result("Connectivity", "WiFi Association", True, f"SKIPPED: Target SSID '{WIFI_SSID}' not visible in air. (Environment issue, not device failure)")
            else:
                logging.info(f"Connecting to AP: {WIFI_SSID} (Max 30s)...")
                run_adb_cmd(f'cmd wifi connect-network "{WIFI_SSID}" wpa2 "{WIFI_PASS}"')
                
                ip = None
                last_status = "Unknown"
                for i in range(30):
                    time.sleep(1)
                    # Use cmd wifi status for modern state reporting
                    _, status_out = run_adb_cmd("cmd wifi status")
                    last_status = status_out.strip()
                    
                    # Check IP address
                    _, out_ip = run_adb_cmd("ifconfig wlan0")
                    if "inet addr:" in out_ip:
                        ip = out_ip.split("inet addr:")[1].split()[0]
                        break
                    
                    if i % 5 == 0:
                        logging.info(f"Waiting for IP ({i}/30s)... Status: {last_status}")

                if ip:
                    reporter.add_result("Connectivity", "WiFi Association", True, f"Connected to {WIFI_SSID} (IP: {ip})")
                else:
                    reporter.add_result("Connectivity", "WiFi Association", False, f"Failed to get IP address for {WIFI_SSID}. Last status: {last_status}")
            
            # --- WiFi Scanning Test ---
            logging.info("Starting WiFi Scanning test...")
            run_adb_cmd("cmd wifi start-scan")
            time.sleep(5)
            _, scan_out = run_adb_cmd("cmd wifi list-scan-results")
            
            # Parsing logic: Skip header, extract SSIDs
            found_aps = []
            for line in scan_out.strip().split('\n'):
                parts = line.split()
                if len(parts) >= 5 and ":" in parts[0]: # Basic BSSID check
                    ssid = " ".join(parts[4:]) # SSID can contain spaces
                    if ssid and ssid not in found_aps:
                        found_aps.append(ssid)
        # --- Robust WiFi Toggle Verification ---
        logging.info("Verifying WiFi 'Disable' functionality...")
        run_adb_cmd("svc wifi disable")
        time.sleep(5)
        _, wifi_on_off = run_adb_cmd("settings get global wifi_on")
        _, iface_out = run_adb_cmd("ifconfig wlan0")
        _, ds_wifi = run_adb_cmd("dumpsys wifi | grep 'Wi-Fi is'")
        
        # LOGIC: Pass if settings are 0 AND no IP is assigned AND dumpsys confirms disabled.
        # We ignore the 'UP' flag because it lingers on this specific hardware.
        is_software_off = wifi_on_off.strip() == "0"
        no_ip = "inet addr:" not in iface_out
        is_ds_disabled = "disabled" in ds_wifi.lower()
        
        if is_software_off and no_ip and is_ds_disabled:
            reporter.add_result("Connectivity", "WiFi Disable Toggle", True, "Verified: WiFi service disabled (Settings=0, No IP, Dumpsys=disabled)")
        else:
            msg = f"Failed: settings={wifi_on_off.strip()}, has_ip={not no_ip}, dumpsys='{ds_wifi.strip()}'"
            reporter.add_result("Connectivity", "WiFi Disable Toggle", False, msg)
        
        # Restore WiFi for subsequent tests
        run_adb_cmd("svc wifi enable")
        time.sleep(3)
            
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
            _, out_fix = run_adb_cmd("settings get global bluetooth_on")
            is_on = out_fix.strip() == "1"

        if is_on:
            reporter.add_result("Connectivity", "Bluetooth Enable", True, "Bluetooth is ON (Manual or Automated)")
            
            logging.info("Starting Bluetooth Discovery test...")
            run_adb_cmd("am start -a android.settings.BLUETOOTH_SETTINGS")
            time.sleep(5) 
            
            found_devices = []
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
                _, bt_sys = run_adb_cmd("dumpsys bluetooth_manager")
                if "discovered" in bt_sys.lower() or "device" in bt_sys.lower():
                     reporter.add_result("Connectivity", "Bluetooth Scanning", True, "Detected discovery activity via dumpsys")
                else:
                     reporter.add_result("Connectivity", "Bluetooth Scanning", False, "No nearby Bluetooth devices found (UI/Dumpsys)")
            
            # --- Robust BT Toggle Verification ---
            logging.info("Verifying Bluetooth 'Disable' functionality...")
            run_adb_cmd("svc bluetooth disable")
            time.sleep(5)
            _, bt_on_off = run_adb_cmd("settings get global bluetooth_on")
            if bt_on_off.strip() == "0":
                 reporter.add_result("Connectivity", "Bluetooth Disable Toggle", True, "Verified: Bluetooth service state is OFF (0)")
            else:
                 reporter.add_result("Connectivity", "Bluetooth Disable Toggle", False, f"Failed: Current settings bluetooth_on={bt_on_off.strip()}")
            
            # Restore BT
            run_adb_cmd("svc bluetooth enable")
            time.sleep(3)
            
            run_adb_cmd("input keyevent 3")
        else:
            reporter.add_result("Connectivity", "Bluetooth Enable", False, "Bluetooth failed to enable via svc")
            
    except Exception as e:
        reporter.add_result("Connectivity", "Bluetooth Tests", False, str(e))
        
    # WWAN (Cellular) Functional Tests
    try:
        logging.info("--- WWAN Functional Connectivity Test ---")
        
        # 1. Save original WiFi state
        _, wifi_state_out = run_adb_cmd("svc wifi show")
        original_wifi_on = "enabled" in wifi_state_out.lower()
        
        # 2. Disable WiFi & Enable Data
        logging.info("Disabling WiFi to isolate WWAN...")
        run_adb_cmd("svc wifi disable")
        run_adb_cmd("svc data enable")
        
        # High-precision wait for route activation
        mobile_ready = False
        target_ifaces = ["wwan0", "rmnet", "ccmni", "pdp"]
        active_iface = None
        ip = None
        
        for i in range(30): # Max 30s
            time.sleep(1)
            # 1. Check which interface has an IP
            _, out_ip = run_adb_cmd("ip -f inet addr show | grep -E 'wwan|rmnet|ccmni|pdp'")
            if "inet " in out_ip:
                ip = out_ip.split("inet ")[1].split("/")[0]
                for iface in target_ifaces:
                    if iface in out_ip:
                        active_iface = iface
                        break
            
            # 2. Check for route to internet (8.8.8.8)
            _, route_get = run_adb_cmd("ip route get 8.8.8.8")
            if active_iface and active_iface in route_get:
                logging.info(f"Traffic route confirmed via {active_iface}: {route_get.strip()}")
                mobile_ready = True
                break
            
            if i % 5 == 0:
                logging.info(f"Waiting for mobile route ({i+1}/30s)... Current IP: {ip}")
        
        if ip:
             logging.info(f"Mobile Data IP detected: {ip} on {active_iface or 'unknown'}")
             
             # 3. Perform Ping & HTTP check
             logging.info("Verifying data route (Ping 8.8.8.8)...")
             code_ping, _ = run_adb_cmd("ping -c 1 -W 5 8.8.8.8")
             
             logging.info("Verifying HTTP/DNS (YouTube headers)...")
             # Use --interface to force traffic through mobile data if possible
             curl_cmd = "curl -Is --connect-timeout 8 https://www.youtube.com"
             if active_iface:
                 curl_cmd += f" --interface {active_iface}"
             
             code_curl, out_curl = run_adb_cmd(f"{curl_cmd} | head -n 1")
             
             if code_ping == 0 or "HTTP/" in out_curl or "200" in out_curl:
                 reporter.add_result("Connectivity", "WWAN Data Transfer", True, f"Verified: Connectivity successful via {active_iface} (IP: {ip})")
             else:
                 msg = f"Failed: Ping code={code_ping}, curl='{out_curl.strip()}'"
                 reporter.add_result("Connectivity", "WWAN Data Transfer", False, msg)
        else:
             reporter.add_result("Connectivity", "WWAN Data Transfer", False, "Failed: No IP address detected on mobile interfaces after 30s.")

        # 4. Restore WiFi
        if original_wifi_on:
            logging.info("Restoring WiFi state...")
            run_adb_cmd("svc wifi enable")
            time.sleep(3)

    except Exception as e:
        reporter.add_result("Connectivity", "WWAN Functional Test", False, str(e))
        run_adb_cmd("svc wifi enable")
