import usb.core
import usb.util
import time
import sys
import logging

# AOA Protocol Constants
ACCESSORY_GET_PROTOCOL = 51
ACCESSORY_SEND_STRING = 52
ACCESSORY_START = 53
ACCESSORY_REGISTER_HID = 54
ACCESSORY_UNREGISTER_HID = 55
ACCESSORY_SET_HID_DESCRIPTOR = 56
ACCESSORY_SEND_HID_EVENT = 57

# Accessory Mode VID/PID
AOA_VID = 0x18D1
AOA_PID_ACC = 0x2D00
AOA_PID_ACC_ADB = 0x2D01
AOA_PID_RECOVERY = 0xD001 

# Trimble T70 specific IDs
TRIMBLE_VID = 0x099e
QUALCOMM_VID = 0x05c6
TRIMBLE_PIDS = [0x02b1, 0x02b3, 0x02b5, 0x02b6, 0x901d]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AOADriver:
    def __init__(self, manufacturer="Google", model="Keyboard", description="USB HID Device", version="1.0", uri="", serial=""):
        self.metadata = [manufacturer, model, description, version, uri, serial]
        self.target_serial = serial
        self.device = None
        self.handle = None

    def find_device(self, vid=None, pid=None, serial=None, allow_recovery=False):
        """Finds the Android device based on VID/PID or serial number."""
        self.device = None
        # Treat empty string as None to match any device
        search_serial = serial if serial else self.target_serial
        if not search_serial:
            search_serial = None
            
        logging.info(f"Searching for USB device (Target Serial: {search_serial})...")
        
        # 1. Check if already in Accessory mode
        kwargs = {"idVendor": AOA_VID}
        if search_serial:
            kwargs["serial_number"] = search_serial
        
        self.device = usb.core.find(**kwargs)
        if self.device and self.device.idProduct in [AOA_PID_ACC, AOA_PID_ACC_ADB]:
            logging.info(f"Device found in Accessory Mode: {hex(self.device.idVendor)}:{hex(self.device.idProduct)}")
            return True

        # 2. Search by Known Identities (Trimble, Qualcomm, etc.)
        if not vid and not pid:
            all_devs = usb.core.find(find_all=True)
            for d in all_devs:
                # 排除 Fastboot 模式以避免誤認 (d001)
                if d.idVendor == AOA_VID and d.idProduct == 0xD001:
                    continue

                is_target = False
                if d.idVendor == TRIMBLE_VID and d.idProduct in TRIMBLE_PIDS:
                    is_target = True
                elif d.idVendor == QUALCOMM_VID and d.idProduct in [0x901d]:
                    is_target = True
                
                if is_target:
                    try:
                        d_serial = d.serial_number
                    except: continue

                    if search_serial:
                        if d_serial == search_serial:
                            self.device = d
                            self.target_serial = search_serial
                            return True
                    else:
                        # Auto-lock onto first compliant device if no serial specified
                        self.device = d
                        self.target_serial = d_serial
                        logging.info(f"Auto-selected device by USB scan: {self.target_serial} (VID={hex(d.idVendor)})")
                        return True
        elif vid and pid:
            kwargs = {"idVendor": vid, "idProduct": pid}
            if search_serial:
                kwargs["serial_number"] = search_serial
            self.device = usb.core.find(**kwargs)
        
        if not self.device:
            logging.error(f"No Android device found on USB bus matching serial {search_serial}.")
            return False
        
        logging.info(f"Connected to device: {hex(self.device.idVendor)}:{hex(self.device.idProduct)}")
        return True

    def is_accessory_mode(self):
        return self.device.idVendor == AOA_VID and self.device.idProduct in [AOA_PID_ACC, AOA_PID_ACC_ADB]

    def switch_to_accessory_mode(self):
        if self.is_accessory_mode():
            return True

        try:
            usb.util.dispose_resources(self.device)
            time.sleep(0.5)
        except: pass

        proto_ver = 0
        for attempt in range(5):
            try:
                protocol = self.device.ctrl_transfer(
                    usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_IN,
                    ACCESSORY_GET_PROTOCOL, 0, 0, 2
                )
                proto_ver = protocol[0] | (protocol[1] << 8)
                logging.info(f"AOA Protocol version: {proto_ver}")
                break
            except Exception as e:
                logging.warning(f"Handshake failed: {e}")
                time.sleep(2)
        
        if proto_ver < 2: return False

        for i, text in enumerate(self.metadata):
            if text:
                self.device.ctrl_transfer(
                    usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_OUT,
                    ACCESSORY_SEND_STRING, 0, i, text.encode('utf-8') + b'\0'
                )
        
        self.device.ctrl_transfer(
            usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_OUT,
            ACCESSORY_START, 0, 0, None
        )

        time.sleep(3)
        self.device = None
        
        # 使用動態參數搜尋以避免空序號問題
        kwargs = {"idVendor": AOA_VID}
        if self.target_serial:
            kwargs["serial_number"] = self.target_serial
            
        for _ in range(10):
            self.device = usb.core.find(**kwargs)
            if self.device and self.device.idProduct in [AOA_PID_ACC, AOA_PID_ACC_ADB]:
                return True
            time.sleep(1)
        return False

    def register_hid(self, hid_id, report_desc):
        if not self.is_accessory_mode(): return False
        self.device.ctrl_transfer(
            usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_OUT,
            ACCESSORY_REGISTER_HID, hid_id, len(report_desc), None
        )
        offset = 0
        chunk_size = 64
        while offset < len(report_desc):
            chunk = report_desc[offset:offset+chunk_size]
            self.device.ctrl_transfer(
                usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_OUT,
                ACCESSORY_SET_HID_DESCRIPTOR, hid_id, offset, chunk
            )
            offset += chunk_size
        # Wait for device to reappear in accessory mode
        time.sleep(1.0)
        return True

    def send_hid_event(self, hid_id, report, retries=3):
        if self.device is None:
            logging.error("No device handle available for HID event.")
            return False
        
        for attempt in range(retries):
            try:
                self.device.ctrl_transfer(
                    usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_OUT,
                    ACCESSORY_SEND_HID_EVENT, hid_id, 0, report
                )
                return True
            except Exception as e:
                if "[Errno 19]" in str(e) or "No such device" in str(e):
                    self.device = None
                time.sleep(0.1)
        return False

KB_REPORT_DESC = bytes([
    0x05, 0x01, 0x09, 0x06, 0xa1, 0x01, 0x05, 0x07,
    0x19, 0xe0, 0x29, 0xe7, 0x15, 0x00, 0x25, 0x01,
    0x75, 0x01, 0x95, 0x08, 0x81, 0x02, 0x95, 0x01,
    0x75, 0x08, 0x81, 0x03, 0x95, 0x05, 0x75, 0x01,
    0x05, 0x08, 0x19, 0x01, 0x29, 0x05, 0x91, 0x02,
    0x95, 0x01, 0x75, 0x03, 0x91, 0x03, 0x95, 0x06,
    0x75, 0x08, 0x15, 0x00, 0x25, 0x65, 0x05, 0x07,
    0x19, 0x00, 0x29, 0x65, 0x81, 0x00, 0xc0
])

CONSUMER_REPORT_DESC = bytes([
    0x05, 0x0c, 0x09, 0x01, 0xa1, 0x01, 0x15, 0x00,
    0x26, 0xff, 0x03, 0x19, 0x00, 0x2a, 0xff, 0x03,
    0x75, 0x10, 0x95, 0x01, 0x81, 0x00, 0xc0
])
