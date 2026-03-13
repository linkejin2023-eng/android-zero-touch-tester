import subprocess
import time
import logging
from typing import Tuple, List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_adb_cmd(cmd: str, timeout: int = 15) -> Tuple[int, str]:
    """Runs an ADB shell command and returns (exit_code, output)"""
    full_cmd = f"adb shell {cmd}"
    try:
        logging.debug(f"Running ADB: {full_cmd}")
        # Python 3.6 doesn't have capture_output=True or text=True
        result = subprocess.run(
            full_cmd, 
            shell=True, 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=timeout
        )
        return result.returncode, result.stdout.strip()
    except subprocess.TimeoutExpired:
        logging.error(f"Command timed out: {full_cmd}")
        return -1, "Timeout"
    except Exception as e:
        logging.error(f"ADB Error: {e}")
        return -1, str(e)

def wait_for_device(timeout: int = 60) -> bool:
    """Waits for an Android device to be connected via ADB."""
    logging.info(f"Waiting for ADB device (timeout={timeout}s)...")
    start = time.time()
    while time.time() - start < timeout:
        result = subprocess.run(
            "adb devices", 
            shell=True, 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        lines = result.stdout.strip().split('\n')
        # Check if there is a device listed that is not offline/unauthorized
        devices = [line for line in lines[1:] if line.strip() and "device" in line and "offline" not in line and "unauthorized" not in line]
        if devices:
            logging.info("Device connected.")
            return True
        time.sleep(2)
    logging.error("No authorized ADB device found.")
    return False

def get_system_property(prop_name: str) -> str:
    _, out = run_adb_cmd(f"getprop {prop_name}")
    return out

def set_system_property(prop_name: str, value: str) -> bool:
    code, _ = run_adb_cmd(f"setprop {prop_name} {value}")
    return code == 0

def check_service_running(service_name: str) -> bool:
    _, out = run_adb_cmd(f"dumpsys {service_name} | head -n 1")
    # If dumpsys says "Can't find service", return False
    return "Can't find service" not in out and out.strip() != ""

def is_screen_on() -> bool:
    _, out = run_adb_cmd("dumpsys power | grep 'mWakefulness='")
    return "Awake" in out

def toggle_screen(turn_on: bool):
    currently_on = is_screen_on()
    if (turn_on and not currently_on) or (not turn_on and currently_on):
        run_adb_cmd("input keyevent 26") # KEYCODE_POWER
        time.sleep(1)
