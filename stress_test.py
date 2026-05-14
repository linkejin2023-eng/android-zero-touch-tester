#!/usr/bin/env python3
import os
import sys
import time
import subprocess
import argparse
from datetime import datetime

def get_battery_temp(serial_args):
    """取得電池溫度作為過熱降頻(Thermal Throttling)的參考指標"""
    try:
        res = subprocess.run(["adb"] + serial_args + ["shell", "dumpsys", "battery"], 
                             capture_output=True, text=True, timeout=5)
        for line in res.stdout.splitlines():
            if "temperature:" in line:
                temp = float(line.split(":")[1].strip()) / 10.0
                return temp
    except Exception:
        pass
    return None

def run_stress_test(args):
    output_base = f"stress_reports/run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(output_base, exist_ok=True)
    
    print(f"=== Starting Stress Test ({args.iterations} Iterations) ===")
    print(f"Target Command: python3 main.py {' '.join(args.main_args)}")
    
    serial_args = []
    if "--serial" in args.main_args:
        idx = args.main_args.index("--serial")
        if idx + 1 < len(args.main_args):
            serial_args = ["-s", args.main_args[idx+1]]
    
    for i in range(1, args.iterations + 1):
        print(f"\n--- Iteration {i}/{args.iterations} ---")
        
        # 紀錄測試前溫度
        temp = get_battery_temp(serial_args)
        if temp:
            print(f"Device Temperature: {temp}°C")
            
        iter_dir = os.path.join(output_base, f"iter_{i:03d}")
        os.makedirs(iter_dir, exist_ok=True)
        
        console_log_path = os.path.join(iter_dir, "console.log")
        cmd = ["python3", "main.py"] + args.main_args
        
        start_time = time.time()
        with open(console_log_path, "w") as log_file:
            process = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT)
            process.wait()
            
        duration = time.time() - start_time
        exit_code = process.returncode
        
        if exit_code != 0:
            print(f"[FAILED] Iteration {i} failed with exit code {exit_code} after {duration:.1f}s.")
            print(f">>> Failure detected. Collecting logs to {iter_dir} ...")
            
            # 1. 抓取 Logcat
            logcat_path = os.path.join(iter_dir, "logcat.txt")
            subprocess.run(["adb"] + serial_args + ["logcat", "-d"], stdout=open(logcat_path, "w"))
            
            # 2. 抓取 Bugreport
            if not args.no_bugreport:
                bugreport_path = os.path.join(iter_dir, f"bugreport_iter_{i}.zip")
                print(">>> Generating bugreport (This may take a few minutes)...")
                subprocess.run(["adb"] + serial_args + ["bugreport", bugreport_path])
                
            print(f"Failure artifacts saved successfully.")
            
            if args.stop_on_fail:
                print("!!! Stop-on-fail triggered. Halting stress test to preserve state. !!!")
                break
        else:
            print(f"[SUCCESS] Iteration {i} passed in {duration:.1f}s.")
            # 成功時刪除 iter 目錄以節省空間
            try:
                os.remove(console_log_path)
                os.rmdir(iter_dir)
            except OSError:
                pass
            
    print(f"\n=== Stress Test Finished. Reports (if any) in {output_base} ===")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stress Test Wrapper for main.py")
    parser.add_argument("-i", "--iterations", type=int, default=10, help="Number of times to run main.py")
    parser.add_argument("--stop-on-fail", action="store_true", help="Stop loop immediately on first failure to preserve device state")
    parser.add_argument("--no-bugreport", action="store_true", help="Skip taking bugreport on fail (saves time and disk space)")
    args, unknown = parser.parse_known_args()
    
    # 將所有未知參數 (unknown) 視為要傳給 main.py 的參數
    args.main_args = unknown
    
    # 移除使用者可能習慣性加上的 '--' 分隔符號
    if args.main_args and args.main_args[0] == "--":
        args.main_args = args.main_args[1:]
        
    run_stress_test(args)
