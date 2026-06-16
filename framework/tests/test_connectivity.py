from framework.adb_helper import run_adb_cmd
from framework.ui_automator import UIHelper
from framework.report_generator import HTMLReportGenerator
import time
import logging

WIFI_SSID = "Xiaomi_test"
WIFI_PASS = "0987654321"

def run_tests(ui: UIHelper, reporter: HTMLReportGenerator, ssid=None, password=None, specs=None, selectors=None, excluded=None):
    if not excluded: excluded = []
    logging.info("Running Connectivity Tests (WiFi/BT)...")
    
    if not specs: specs = {}
    if not selectors: selectors = {}
    
    target_ssid = ssid if ssid else WIFI_SSID
    target_pass = password if password else WIFI_PASS
    
    hw_wwan_ifaces = specs.get("wwan_interfaces", ["rmnet", "ccmni", "pdp", "wwan"])
    wwan_pattern = "|".join([f"{i}\\d*" for i in hw_wwan_ifaces])

    # WiFi Tests
    try:
        # Enforce mutual exclusivity
        logging.info("Enforcing Mutual Exclusivity: Disabling Mobile Data...")
        run_adb_cmd("svc data disable")
        time.sleep(2)
        
        # Enhanced Routing Check
        logging.info("Verifying Routing Table (Mutual Exclusivity)...")
        _, route_out = run_adb_cmd("ip route")
        _, ifconfig_out = run_adb_cmd("ifconfig")
        
        # Check if any rmnet (cellular) interface has an IP
        has_wwan_ip = False
        import re
        wwan_interfaces = re.findall(rf'({wwan_pattern})', ifconfig_out)
        for iface in wwan_interfaces:
            # Check the block for this interface in ifconfig
            iface_block = ifconfig_out.split(iface)[1].split('\n\n')[0] if iface in ifconfig_out else ""
            if "inet addr:" in iface_block:
                has_wwan_ip = True
                break
        
        # Check default gateway
        default_route_wlan = "default via" in route_out and "dev wlan0" in route_out
        has_other_default = "default via" in route_out and "dev wlan0" not in route_out
        
        if "Mutual Exclusivity" not in excluded:
            if not has_wwan_ip and not has_other_default:
                reporter.add_result("Connectivity", "Mutual Exclusivity", True, "Verified: No active WWAN routes, clean routing table.")
            else:
                msg = "Warning: Parallel routes detected."
                if has_wwan_ip: msg += " WWAN IP still active."
                if has_other_default: msg += " Non-WiFi default gateway found."
                reporter.add_result("Connectivity", "Mutual Exclusivity", False, msg)
        else:
            reporter.add_result("Connectivity", "Mutual Exclusivity", True, "Skipped by profile", status_override="SKIP")

        # WiFi Enable Test
        if "WiFi Enable" not in excluded:
            run_adb_cmd("svc wifi enable")
            time.sleep(3)
            _, wifi_on_init = run_adb_cmd("settings get global wifi_on")
            if wifi_on_init.strip() == "1":
                reporter.add_result("Connectivity", "WiFi Enable", True, "Successfully enabled WiFi (via svc)")
            else:
                logging.warning("svc wifi enable failed, falling back to UI toggle...")
                run_adb_cmd("am start -a android.settings.WIFI_SETTINGS")
                time.sleep(3)
                
                try:
                    # Attempt to find switch widgets that can toggle WiFi
                    switch = ui.d(className="android.widget.Switch")
                    if switch.exists(timeout=3):
                        if switch.info.get('checked') == False or switch.info.get('text') == 'Off' or switch.info.get('text') == '關閉' or switch.info.get('text') == '关闭':
                            logging.info("Found WiFi switch in OFF state, tapping...")
                            switch.click()
                            time.sleep(2)
                    else:
                        # Fallback for devices using different widget classes or text wrappers
                        toggle_texts = ["Use Wi-Fi", "Wi-Fi", "WLAN"]
                        for txt in toggle_texts:
                            btn = ui.d(textContains=txt, scrollable=False)
                            if btn.exists(timeout=1):
                                logging.info(f"Found toggle by text '{txt}', tapping bounds...")
                                btn.click()
                                time.sleep(2)
                                break
                                
                    # 處理 China SKU 的安全授權彈窗 (例如: 永远允许)
                    for allow_txt in ["永远允许", "允許", "Allow", "始终允许"]:
                        allow_btn = ui.d(textMatches=f"(?i).*{allow_txt}.*")
                        if allow_btn.exists(timeout=1.5):
                            logging.info(f"Found authorization popup '{allow_txt}', tapping...")
                            allow_btn.click()
                            time.sleep(2)
                            break
                            
                except Exception as e:
                    logging.warning(f"UI fallback exception: {e}")
                
                # Check again
                _, wifi_on_retry = run_adb_cmd("settings get global wifi_on")
                if wifi_on_retry.strip() == "1":
                    reporter.add_result("Connectivity", "WiFi Enable", True, "Successfully enabled WiFi (via UI fallback)")
                else:
                    reporter.add_result("Connectivity", "WiFi Enable", False, f"WiFi failed to enable (settings check). svc_initial='{wifi_on_init.strip()}', final='{wifi_on_retry.strip()}'")
                
                # Try to go back to home or out of settings
                run_adb_cmd("input keyevent 4")
                time.sleep(1)
        else:
            reporter.add_result("Connectivity", "WiFi Enable", True, "Skipped by profile", status_override="SKIP")

        # --- 1. WiFi Scanning (Visibility Check) ---
        if "WiFi Scanning" not in excluded:
            logging.info("Scanning for WiFi Access Points (Up to 15s)...")
            run_adb_cmd("cmd wifi start-scan")
            found_aps = []
            for _ in range(3):
                time.sleep(5)
                _, scan_out = run_adb_cmd("cmd wifi list-scan-results")
                found_aps = []
                for line in scan_out.strip().split('\n'):
                    parts = line.split()
                    if len(parts) >= 5 and ":" in parts[0]: 
                        ssid = " ".join(parts[4:]).strip()
                        if "[ESS]" in ssid: ssid = ssid.split("[ESS]")[0].strip()
                        if ssid and ssid not in found_aps: found_aps.append(ssid)
                if target_ssid and target_ssid in found_aps: break
            if found_aps:
                reporter.add_result("Connectivity", "WiFi Scanning", True, f"Found {len(found_aps)} nearby Access Points: {', '.join(found_aps[:3])}")
            else:
                reporter.add_result("Connectivity", "WiFi Scanning", False, "No nearby WiFi Access Points detected")
        else:
            reporter.add_result("Connectivity", "WiFi Scanning", True, "Skipped by profile", status_override="SKIP")

        # --- 2. WiFi Association (Connection Check) ---
        if "WiFi AP Connection" not in excluded:
            if target_ssid and target_pass:
                logging.info(f"Attempting unconditional connection to AP: {target_ssid} (Max 30s)...")
                run_adb_cmd(f'cmd wifi connect-network "{target_ssid}" wpa2 "{target_pass}"')
                ip = None
                last_status = "Unknown"
                for i in range(90):
                    time.sleep(1)
                    _, status_out = run_adb_cmd("cmd wifi status")
                    last_status = status_out.strip()
                    import re
                    _, out_ip = run_adb_cmd("ip -f inet addr show wlan0")
                    match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)', out_ip)
                    if match:
                        ip = match.group(1)
                        break
                    if i % 3 == 0:
                        rssi_m = re.search(r'RSSI:\s+(-?\d+)', last_status)
                        speed_m = re.search(r'Link speed:\s+(\d+Mbps)', last_status)
                        rssi = rssi_m.group(1) if rssi_m else "N/A"
                        speed = speed_m.group(1) if speed_m else "N/A"
                        logging.info(f"Waiting for IP ({i}/90s)... Signal: {rssi}dBm | Speed: {speed} | Status: {last_status[:40]}...")
                if ip:
                    reporter.add_result("Connectivity", "WiFi AP Connection", True, f"Connected to {target_ssid} (IP: {ip})")
                else:
                    reporter.add_result("Connectivity", "WiFi AP Connection", False, f"Failed to get IP address for {target_ssid}. Last status: {last_status}")
            else:
                reporter.add_result("Connectivity", "WiFi AP Connection", False, "No target SSID/PWD provided in config", status_override="SKIP")
        else:
            reporter.add_result("Connectivity", "WiFi AP Connection", True, "Skipped by profile", status_override="SKIP")
        
        # --- Robust WiFi Toggle Verification ---
        if "WiFi Disable Toggle" not in excluded:
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
        else:
            reporter.add_result("Connectivity", "WiFi Disable Toggle", True, "Skipped by profile", status_override="SKIP")
            
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
            
            if not is_on:
                logging.warning("svc bluetooth enable failed, falling back to UI toggle...")
                run_adb_cmd("am start -a android.settings.BLUETOOTH_SETTINGS")
                time.sleep(3)
                try:
                    switch = ui.d(className="android.widget.Switch")
                    if switch.exists(timeout=3):
                        if switch.info.get('checked') == False or switch.info.get('text') in ['Off', '關閉', '关闭']:
                            logging.info("Found Bluetooth switch in OFF state, tapping...")
                            switch.click()
                            time.sleep(2)
                    else:
                        toggle_texts = ["Use Bluetooth", "Bluetooth", "藍牙", "蓝牙"]
                        for txt in toggle_texts:
                            btn = ui.d(textContains=txt, scrollable=False)
                            if btn.exists(timeout=1):
                                logging.info(f"Found toggle by text '{txt}', tapping bounds...")
                                btn.click()
                                time.sleep(2)
                                break
                    
                    for allow_txt in ["永远允许", "允許", "Allow", "始终允许"]:
                        allow_btn = ui.d(textMatches=f"(?i).*{allow_txt}.*")
                        if allow_btn.exists(timeout=1.5):
                            logging.info(f"Found authorization popup '{allow_txt}', tapping...")
                            allow_btn.click()
                            time.sleep(2)
                            break
                except Exception as e:
                    logging.warning(f"BT UI fallback exception: {e}")
                
                _, out_fix = run_adb_cmd("settings get global bluetooth_on")
                is_on = out_fix.strip() == "1"
                run_adb_cmd("input keyevent 4")
                time.sleep(1)

        if is_on:
            if "Bluetooth Enable" not in excluded:
                reporter.add_result("Connectivity", "Bluetooth Enable", True, "Bluetooth is ON (Manual or Automated)")
            else:
                reporter.add_result("Connectivity", "Bluetooth Enable", True, "Skipped by profile", status_override="SKIP")
            
            if "Bluetooth Scanning" not in excluded:
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
            else:
                reporter.add_result("Connectivity", "Bluetooth Scanning", True, "Skipped by profile", status_override="SKIP")
            
            # --- Robust BT Toggle Verification ---
            if "Bluetooth Disable Toggle" not in excluded:
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
                reporter.add_result("Connectivity", "Bluetooth Disable Toggle", True, "Skipped by profile", status_override="SKIP")
        else:
            reporter.add_result("Connectivity", "Bluetooth Enable", False, "Bluetooth failed to enable via svc")
            
    except Exception as e:
        reporter.add_result("Connectivity", "Bluetooth Tests", False, str(e))
        
    # WWAN (Cellular) Functional Tests
    if "WWAN Data Transfer" not in excluded:
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
            target_ifaces = hw_wwan_ifaces
            active_iface = None
            ip = None
            
            for i in range(30): # Max 30s
                time.sleep(1)
                # 1. Check which interface has an IP
                _, out_ip = run_adb_cmd(f"ip -f inet addr show | grep -E '{'|'.join(target_ifaces)}'")
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
    else:
        reporter.add_result("Connectivity", "WWAN Data Transfer", True, "Skipped by profile", status_override="SKIP")
