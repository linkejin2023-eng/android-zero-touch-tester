import subprocess
import time
import logging
from typing import Tuple, List

GLOBAL_SERIAL = None

def set_global_serial(serial: str):
    global GLOBAL_SERIAL
    GLOBAL_SERIAL = serial
    if serial:
        logging.info(f"Target serial set to: {serial}")

def run_local_adb(args_list: List[str], timeout: int = 15):
    """Runs a local adb command with arguments list and returns a CompletedProcess object."""
    cmd = ["adb"] + args_list
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except Exception as e:
        logging.error(f"Local ADB Error: {e}")
        return subprocess.CompletedProcess(cmd, -1, stdout="", stderr=str(e))

def list_adb_devices() -> List[str]:
    """Returns a list of connected ADB device serials."""
    res = run_local_adb(["devices"])
    serials = []
    if res.returncode == 0:
        for line in res.stdout.splitlines():
            if "\tdevice" in line:
                serials.append(line.split("\t")[0])
    return serials

def run_adb_cmd(cmd: str, timeout: int = 15) -> Tuple[int, str]:
    """Runs an ADB shell command and returns (exit_code, output)"""
    adb_base = "adb"
    if GLOBAL_SERIAL:
        adb_base = f"adb -s {GLOBAL_SERIAL}"
    
    full_cmd = f"{adb_base} shell {cmd}"
    try:
        logging.debug(f"Running ADB: {full_cmd}")
        # Use subprocess.run for better control
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

def adb_pull(remote_path: str, local_path: str, timeout: int = 60) -> bool:
    """Pulls a file from device using the global serial."""
    cmd = ["adb"]
    if GLOBAL_SERIAL:
        cmd.extend(["-s", GLOBAL_SERIAL])
    cmd.extend(["pull", remote_path, local_path])
    try:
        subprocess.run(cmd, capture_output=True, check=True, timeout=timeout)
        return True
    except Exception as e:
        logging.error(f"ADB Pull Failed: {e}")
        return False

def adb_push(local_path: str, remote_path: str, timeout: int = 60) -> bool:
    """Pushes a file to device using the global serial."""
    cmd = ["adb"]
    if GLOBAL_SERIAL:
        cmd.extend(["-s", GLOBAL_SERIAL])
    cmd.extend(["push", local_path, remote_path])
    try:
        subprocess.run(cmd, capture_output=True, check=True, timeout=timeout)
        return True
    except Exception as e:
        logging.error(f"ADB Push Failed: {e}")
        return False

def wait_for_device(timeout: int = 300) -> bool:
    """Blocks until an authorized ADB device is found or timeout reached."""
    start_time = time.time()
    
    adb_base = "adb"
    if GLOBAL_SERIAL:
        adb_base = f"adb -s {GLOBAL_SERIAL}"
        logging.info(f"[{GLOBAL_SERIAL}] Waiting for ADB device (timeout={timeout}s)...")
    else:
        logging.info(f"Waiting for ANY ADB device (timeout={timeout}s)...")

    while time.time() - start_time < timeout:
        try:
            # Correctly build the command list
            cmd = ["adb"]
            if GLOBAL_SERIAL:
                cmd.extend(["-s", GLOBAL_SERIAL])
            cmd.append("devices")
            
            output = subprocess.check_output(cmd).decode()
            
            # If we have a serial, check for THAT specific serial
            if GLOBAL_SERIAL:
                if f"{GLOBAL_SERIAL}\tdevice" in output:
                    return True
            else:
                # Fallback: check if ANY device is ready
                for line in output.splitlines():
                    if "\tdevice" in line:
                        return True
        except Exception as e:
            logging.debug(f"wait_for_device polling error: {e}")
            pass
        time.sleep(2)
    return False

def get_system_property(prop_name: str) -> str:
    _, out = run_adb_cmd(f"getprop {prop_name}")
    return out

def set_system_property(prop_name: str, value: str) -> bool:
    code, _ = run_adb_cmd(f"setprop {prop_name} {value}")
    return code == 0

def check_service_running(service_name: str) -> bool:
    _, out = run_adb_cmd(f"dumpsys {service_name} | head -n 1")
    return "Can't find service" not in out and out.strip() != ""

def is_screen_on() -> bool:
    _, out = run_adb_cmd("dumpsys power | grep 'mWakefulness='")
    return "Awake" in out

def toggle_screen(turn_on: bool):
    currently_on = is_screen_on()
    if (turn_on and not currently_on) or (not turn_on and currently_on):
        run_adb_cmd("input keyevent 26") # KEYCODE_POWER
        time.sleep(1)

def unlock_device():
    """Unlocks the device by waking it up, dismissing keyguard, and swiping."""
    run_adb_cmd("input keyevent 224") # KEYCODE_WAKEUP
    time.sleep(1)
    run_adb_cmd("wm dismiss-keyguard")
    time.sleep(1)
    _, size_out = run_adb_cmd("wm size")
    try:
        if "Physical size" in size_out:
            dims = [int(s) for s in size_out.split(":")[-1].strip().split("x")]
            w, h = dims[0], dims[1]
            run_adb_cmd(f"input swipe {w//2} {h-200} {w//2} 200")
            time.sleep(1)
    except Exception:
        pass

def get_stay_on_state() -> str:
    _, out = run_adb_cmd("settings get global stay_on_while_plugged_in")
    return out.strip()

def set_stay_on_state(value: str):
    run_adb_cmd(f"settings put global stay_on_while_plugged_in {value}")

def keep_screen_on(enable: bool):
    """Forces the screen to stay awake (or restores state)."""
    if enable:
        # 3 (AC) | 2 (USB) | 1 (Wireless) = 7
        run_adb_cmd("settings put global stay_on_while_plugged_in 7")
        run_adb_cmd("input keyevent 224") # Wake up
    else:
        run_adb_cmd("settings put global stay_on_while_plugged_in 0")
