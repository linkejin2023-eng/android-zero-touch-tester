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

# Accessory Mode VID/PID (Fixed for all Android devices in accessory mode)
AOA_VID = 0x18D1
AOA_PID_ACC = 0x2D00
AOA_PID_ACC_ADB = 0x2D01

# Trimble T70 specific IDs
TRIMBLE_VID = 0x099e
QUALCOMM_VID = 0x05c6
TRIMBLE_PIDS = [0x02b1, 0x02b5, 0x901d] # 02b1: Standard/OOBE, 02b5: ADB, 901d: Userdebug/Diag

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AOADriver:
    def __init__(self, manufacturer="Google", model="Keyboard", description="USB HID Device", version="1.0", uri="", serial=""):
        self.metadata = [manufacturer, model, description, version, uri, serial]
        self.device = None
        self.handle = None

    def find_device(self, vid=None, pid=None):
        """Finds the Android device based on VID/PID or common patterns."""
        # First, check if already in Accessory mode
        logging.info("Checking if device is already in Accessory Mode...")
        self.device = usb.core.find(idVendor=AOA_VID)
        if self.device and self.device.idProduct in [AOA_PID_ACC, AOA_PID_ACC_ADB]:
            logging.info(f"Device found in Accessory Mode: {hex(self.device.idVendor)}:{hex(self.device.idProduct)}")
            return True

        # Prioritize Trimble devices if no specific VID/PID is given
        if not vid and not pid:
            logging.info("Prioritizing search for Trimble devices...")
            for p in TRIMBLE_PIDS:
                self.device = usb.core.find(idVendor=TRIMBLE_VID, idProduct=p)
                if self.device:
                    logging.info(f"Found Trimble device: {hex(TRIMBLE_VID)}:{hex(p)}")
                    return True

        if vid and pid:
            logging.info(f"Looking for specific device {hex(vid)}:{hex(pid)}...")
            self.device = usb.core.find(idVendor=vid, idProduct=pid)
        else:
            logging.info("Scanning for any Android device...")
            # Common Android VIDs: Google (0x18d1), Samsung (0x04e8), Trimble (0x099e), etc.
            # We can search for devices with USB_CLASS_COMM (0x02) or other specific descriptors
            # For now, we rely on the specific VID/PID provided by user or common ones
            vids = [0x18D1, 0x099E, 0x05C6, 0x04E8, 0x0BB4, 0x22B8, 0x1949]
            for v in vids:
                self.device = usb.core.find(idVendor=v)
                if self.device:
                    # 如果是 Qualcomm VID，額外確認 PID 是否在 Trimble 範疇內
                    if v == QUALCOMM_VID and self.device.idProduct not in TRIMBLE_PIDS:
                        self.device = None
                        continue
                    break
        
        if not self.device:
            logging.error("No Android device found.")
            return False
        
        logging.info(f"Connected to device: {hex(self.device.idVendor)}:{hex(self.device.idProduct)}")
        return True

    def is_accessory_mode(self):
        """Checks if the device is already in Accessory Mode."""
        return self.device.idVendor == AOA_VID and self.device.idProduct in [AOA_PID_ACC, AOA_PID_ACC_ADB]

    def switch_to_accessory_mode(self):
        """Performs the AOA handshake to switch device to Accessory Mode."""
        if self.is_accessory_mode():
            logging.info("Device is already in Accessory Mode.")
            return True

        # 1. Get Protocol
        try:
            protocol = self.device.ctrl_transfer(
                usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_IN,
                ACCESSORY_GET_PROTOCOL, 0, 0, 2
            )
            proto_ver = protocol[0] | (protocol[1] << 8)
            logging.info(f"AOA Protocol version: {proto_ver}")
            if proto_ver < 2:
                logging.error("Device does not support AOA 2.0 (Required for HID)")
                return False
        except Exception as e:
            logging.error(f"Failed to get AOA protocol: {e}")
            return False

        # 2. Send Metadata Strings
        for i, text in enumerate(self.metadata):
            if text:
                self.device.ctrl_transfer(
                    usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_OUT,
                    ACCESSORY_SEND_STRING, 0, i, text.encode('utf-8') + b'\0'
                )
        
        # 3. Start Accessory
        logging.info("Sending Start Accessory request...")
        self.device.ctrl_transfer(
            usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_OUT,
            ACCESSORY_START, 0, 0, None
        )

        # Wait for device to disconnect and reconnect
        logging.info("Waiting for device to reconnect in Accessory Mode...")
        time.sleep(3)
        
        # Re-find the device with AOA VID/PID
        self.device = None
        for _ in range(10):
            self.device = usb.core.find(idVendor=AOA_VID)
            if self.device and self.device.idProduct in [AOA_PID_ACC, AOA_PID_ACC_ADB]:
                logging.info(f"Device reconnected in Accessory Mode: {hex(self.device.idVendor)}:{hex(self.device.idProduct)}")
                return True
            time.sleep(1)
        
        logging.error("Device failed to reconnect in Accessory Mode.")
        return False

    def register_hid(self, hid_id, report_desc):
        """Registers a virtual HID device on the Android accessory."""
        if not self.is_accessory_mode():
            logging.error("Device must be in Accessory Mode to register HID.")
            return False
        
        logging.info(f"Registering HID ID {hid_id} with report descriptor length {len(report_desc)}...")
        # ACCESSORY_REGISTER_HID: index=hid_id, value=descriptor_length
        self.device.ctrl_transfer(
            usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_OUT,
            ACCESSORY_REGISTER_HID, hid_id, len(report_desc), None
        )
        
        # ACCESSORY_SET_HID_DESCRIPTOR: index=hid_id, value=offset
        # Send descriptor in chunks if necessary (max 64 bytes for control transfers usually)
        offset = 0
        chunk_size = 64
        while offset < len(report_desc):
            chunk = report_desc[offset:offset+chunk_size]
            self.device.ctrl_transfer(
                usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_OUT,
                ACCESSORY_SET_HID_DESCRIPTOR, hid_id, offset, chunk
            )
            offset += chunk_size
            
        logging.info("HID Registration complete.")
        time.sleep(1) # Extra buffer for Android to initialize the virtual device
        return True

    def send_hid_event(self, hid_id, report, retries=3):
        """Sends a HID event (report) to the Android device with retry logic."""
        for attempt in range(retries):
            if not self.device:
                logging.error("No device handle available for HID event.")
                return False
            try:
                self.device.ctrl_transfer(
                    usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_OUT,
                    ACCESSORY_SEND_HID_EVENT, hid_id, 0, report
                )
                return True
            except Exception as e:
                # If device is gone, reset handle
                if "[Errno 19]" in str(e) or "No such device" in str(e):
                    self.device = None
                
                if attempt < retries - 1:
                    logging.warning(f"HID event failed (attempt {attempt+1}), retrying... Error: {e}")
                    time.sleep(0.1)
                else:
                    logging.error(f"Failed to send HID event after {retries} attempts: {e}")
                    return False

# Standard USB HID Keyboard Descriptor
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

# HID Consumer Page Descriptor (16-bit Usage ID Array)
CONSUMER_REPORT_DESC = bytes([
    0x05, 0x0c,        # Usage Page (Consumer)
    0x09, 0x01,        # Usage (Consumer Control)
    0xa1, 0x01,        # Collection (Application)
    0x15, 0x00,        #   Logical Minimum (0)
    0x26, 0xff, 0x03,  #   Logical Maximum (0x03FF)
    0x19, 0x00,        #   Usage Minimum (0)
    0x2a, 0xff, 0x03,  #   Usage Maximum (0x03FF)
    0x75, 0x10,        #   Report Size (16)
    0x95, 0x01,        #   Report Count (1)
    0x81, 0x00,        #   Input (Data, Ary, Abs)
    0xc0               # End Collection
])

if __name__ == "__main__":
    driver = AOADriver()
    # Replace with the user's Trimble VID/PID
    if driver.find_device(vid=0x099E, pid=0x02B1):
        if driver.switch_to_accessory_mode():
            driver.register_hid(1, KB_REPORT_DESC)
            logging.info("Driver ready. Test complete.")
