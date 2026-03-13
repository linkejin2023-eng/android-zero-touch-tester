#!/usr/bin/env python3
import sys
import subprocess
import os
import shutil

def check_command(cmd):
    path = shutil.which(cmd)
    if path:
        print(f"[OK] {cmd} found at: {path}")
        return True
    else:
        print(f"[FAIL] {cmd} NOT FOUND in PATH.")
        return False

def check_usb_permissions():
    print("Checking USB permissions for AOA/Trimble...")
    udev_file = "/etc/udev/rules.d/51-android-aoa.rules"
    if os.path.exists(udev_file):
        print(f"[OK] Udev rules exist: {udev_file}")
    else:
        print("[WARNING] Udev rules NOT FOUND. PyUSB might fail with Access Denied.")
        print(" -> Run: bash hid_gadget/setup_permissions.sh")

def check_dependencies():
    print("Checking Python dependencies...")
    try:
        import usb.core
        print("[OK] pyusb installed.")
    except ImportError:
        print("[FAIL] pyusb NOT FOUND.")
    
    try:
        import uiautomator2
        print("[OK] uiautomator2 installed.")
    except ImportError:
        print("[FAIL] uiautomator2 NOT FOUND.")

def main():
    print("=== Environment Diagnostic Tool ===\n")
    
    check_command("adb")
    check_command("fastboot")
    print("")
    
    check_usb_permissions()
    print("")
    
    check_dependencies()
    print("\n================================")
    print("If everything is [OK], you are ready to use the tool.")

if __name__ == "__main__":
    main()
