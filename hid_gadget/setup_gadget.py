import os
import time

def setup_gadget():
    """
    Sets up the Linux USB Gadget API (ConfigFS) to emulate a USB HID Keyboard.
    Run this script with root privileges.
    """
    g_path = "/sys/kernel/config/usb_gadget/android_test_hid"
    
    if os.path.exists(g_path):
        print("Gadget already exists. Tearing down...")
        os.system(f"rm {g_path}/configs/c.1/hid.usb0")
        os.system(f"rmdir {g_path}/configs/c.1/strings/0x409")
        os.system(f"rmdir {g_path}/configs/c.1")
        os.system(f"rmdir {g_path}/functions/hid.usb0")
        os.system(f"rmdir {g_path}/strings/0x409")
        os.system(f"rmdir {g_path}")

    print("Configuring new USB HID Gadget...")
    os.makedirs(g_path, exist_ok=True)

    # Device configuration
    write_val(f"{g_path}/idVendor", "0x1d6b")   # Linux Foundation
    write_val(f"{g_path}/idProduct", "0x0104")  # Multifunction Composite Gadget
    write_val(f"{g_path}/bcdDevice", "0x0100")
    write_val(f"{g_path}/bcdUSB", "0x0200")

    # English strings
    os.makedirs(f"{g_path}/strings/0x409", exist_ok=True)
    write_val(f"{g_path}/strings/0x409/serialnumber", "fedcba9876543210")
    write_val(f"{g_path}/strings/0x409/manufacturer", "AntigravityQA")
    write_val(f"{g_path}/strings/0x409/product", "QA Auto Keyboard")

    # Functions (HID)
    os.makedirs(f"{g_path}/functions/hid.usb0", exist_ok=True)
    write_val(f"{g_path}/functions/hid.usb0/protocol", "1")   # Keyboard
    write_val(f"{g_path}/functions/hid.usb0/subclass", "1")   # Boot interface
    write_val(f"{g_path}/functions/hid.usb0/report_length", "8")
    
    # Keyboard Report Descriptor
    report_desc = bytes([
        0x05, 0x01, 0x09, 0x06, 0xa1, 0x01, 0x05, 0x07,
        0x19, 0xe0, 0x29, 0xe7, 0x15, 0x00, 0x25, 0x01,
        0x75, 0x01, 0x95, 0x08, 0x81, 0x02, 0x95, 0x01,
        0x75, 0x08, 0x81, 0x03, 0x95, 0x05, 0x75, 0x01,
        0x05, 0x08, 0x19, 0x01, 0x29, 0x05, 0x91, 0x02,
        0x95, 0x01, 0x75, 0x03, 0x91, 0x03, 0x95, 0x06,
        0x75, 0x08, 0x15, 0x00, 0x25, 0x65, 0x05, 0x07,
        0x19, 0x00, 0x29, 0x65, 0x81, 0x00, 0xc0
    ])
    with open(f"{g_path}/functions/hid.usb0/report_desc", "wb") as f:
        f.write(report_desc)

    # Config c.1
    os.makedirs(f"{g_path}/configs/c.1/strings/0x409", exist_ok=True)
    write_val(f"{g_path}/configs/c.1/strings/0x409/configuration", "Config 1: Keyboard")
    write_val(f"{g_path}/configs/c.1/MaxPower", "250")

    # Link function to config
    os.symlink(f"{g_path}/functions/hid.usb0", f"{g_path}/configs/c.1/hid.usb0")

    # Bind to UDC (USB Device Controller - this varies by motherboard, trying to find first available)
    udc_dir = "/sys/class/udc"
    if os.path.exists(udc_dir):
        udcs = os.listdir(udc_dir)
        if udcs:
            write_val(f"{g_path}/UDC", udcs[0])
            print(f"Gadget bound to UDC: {udcs[0]}")
            print("Keyboard ready at /dev/hidg0. Please connect the Android device.")
            return True
        else:
            print("Error: No USB Device Controller (UDC) found on this Linux machine.")
            print("Make sure this PC supports OTG/Device mode or load the dummy_hcd kernel module for testing.")
            return False
    else:
        print("Error: /sys/class/udc does not exist. Your kernel might not support USB Gadget.")
        return False

def write_val(path, val):
    try:
        with open(path, "w") as f:
            f.write(val)
    except IOError as e:
        print(f"Warning: Could not write {val} to {path}: {e}")

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("This script requires root privileges (sudo).")
        exit(1)
    setup_gadget()
