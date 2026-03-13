from oobe_bypass_script import OOBEBypass, KEY_TAB, KEY_ENTER, KEY_DOWN, KEY_UP, MOD_LMETA, KEY_LEFT, KEY_RIGHT, KEY_ESC, KEY_SPACE, KEY_I, KEY_N, KEY_D, KEY_H, KEY_BACKSPACE
from aoa_driver import AOADriver, KB_REPORT_DESC, CONSUMER_REPORT_DESC
import logging
import sys
import tty
import termios
import time

def getch():
    """Reads a single character from stdin."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def recorder():
    logging.basicConfig(level=logging.INFO)
    driver = AOADriver()
    if not driver.find_device(vid=0x099E, pid=0x02B1):
        return
    
    if not driver.switch_to_accessory_mode():
        return
        
    driver.register_hid(1, KB_REPORT_DESC)
    driver.register_hid(2, CONSUMER_REPORT_DESC)
    bypass = OOBEBypass(driver)
    
    print("\n=== ADB 開啟序列錄製器 (進階精準版) ===")
    print("請看著手機螢幕，使用電腦鍵盤控制：")
    print("- [t]: 發送 TAB (切換焦點)")
    print("- [e]: 發送 ENTER (點選/確認)")
    print("- [d]: 發送 DOWN (向下移動)")
    print("- [u]: 發送 UP (向上移動)")
    print("- [l]: 發送 LEFT (向左移動)")
    print("- [r]: 發送 RIGHT (向右移動)")
    print("- [h]: 發送系統 HOME (Consumer Page)")
    print("- [b]: 發送系統 BACK (Consumer Page)")
    print("- [w]: 發送 Meta/Win 鍵 (原有方式)")
    print("- [k]: 發送 ESC 鍵 (原有方式)")
    print("- [i]: 直接開啟 SETTINGS (Win+I)")
    print("- [s]: 發送 SEARCH (Win+Space)")
    print("- [x]: 發送 MULTI-ENTER (連點 7 次)")
    print("- [q]: 結束錄製並顯示序列")
    print("========================\n")
    
    sequence = []
    
    while True:
        char = getch()
        key_cmd = None
        if char == 't':
            bypass.press_key(KEY_TAB)
            key_cmd = "TAB"
        elif char == 'e':
            bypass.press_key(KEY_ENTER)
            key_cmd = "ENTER"
        elif char == 'd':
            bypass.press_key(KEY_DOWN)
            key_cmd = "DOWN"
        elif char == 'u':
            bypass.press_key(KEY_UP)
            key_cmd = "UP"
        elif char == 'l':
            bypass.press_key(KEY_LEFT)
            key_cmd = "LEFT"
        elif char == 'r':
            bypass.press_key(KEY_RIGHT)
            key_cmd = "RIGHT"
        elif char == 'h':
            # Consumer Page Home
            bypass.press_home()
            key_cmd = "SYS_HOME"
        elif char == 'b':
            # Consumer Page Back
            bypass.press_back()
            key_cmd = "SYS_BACK"
        elif char == 'w':
            bypass.press_key(0, MOD_LMETA)
            key_cmd = "META"
        elif char == 'k':
            bypass.press_key(KEY_ESC)
            key_cmd = "ESC"
        elif char == 'i':
            bypass.press_key(KEY_I, MOD_LMETA)
            key_cmd = "SETTINGS"
        elif char == 's':
            bypass.press_key(KEY_SPACE, MOD_LMETA)
            key_cmd = "SEARCH"
        elif char == 'x':
            for _ in range(7):
                bypass.press_key(KEY_ENTER)
                time.sleep(0.1)
            key_cmd = "MULTI_ENTER"
        elif char == 'q':
            break
            
        if key_cmd:
            sequence.append(key_cmd)
            print(f"已記錄第 {len(sequence)} 個動作: [{key_cmd}]")
            
    print("\n--- 錄製完成 ---")
    print(f"總共記錄了 {len(sequence)} 個動作。")
    print("請將以下序列完整複製給我：\n")
    print(" -> ".join(sequence))
    print("\n========================\n")

if __name__ == "__main__":
    recorder()
