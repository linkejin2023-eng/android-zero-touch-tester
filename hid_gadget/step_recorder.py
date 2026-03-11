from oobe_bypass_script import OOBEBypass, KEY_TAB, KEY_ENTER, KEY_DOWN, KEY_UP, MOD_LMETA
from aoa_driver import AOADriver, KB_REPORT_DESC
import logging
import sys
import tty
import termios

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
    if not driver.find_android_device(vid=0x099E, pid=0x02B1):
        return
    
    if not driver.switch_to_accessory_mode():
        return
        
    driver.register_hid(1, KB_REPORT_DESC)
    bypass = OOBEBypass(driver)
    
    print("\n=== OOBE 序列錄製器 ===")
    print("請看著手機螢幕，使用電腦鍵盤控制：")
    print("- [t]: 發送 TAB (切換按鈕)")
    print("- [e]: 發送 ENTER (點擊)")
    print("- [d]: 發送 DOWN (向下捲動)")
    print("- [h]: 發送 HOME (回起點)")
    print("- [q]: 結束錄製並顯示序列")
    print("========================\n")
    
    sequence = []
    
    while True:
        char = getch()
        if char == 't':
            bypass.press_key(KEY_TAB)
            sequence.append("TAB")
            print("發送: TAB")
        elif char == 'e':
            bypass.press_key(KEY_ENTER)
            sequence.append("ENTER")
            print("發送: ENTER")
        elif char == 'd':
            bypass.press_key(KEY_DOWN)
            sequence.append("DOWN")
            print("發送: DOWN")
        elif char == 'h':
            bypass.press_key(0, MOD_LMETA)
            sequence.append("HOME")
            print("發送: HOME")
        elif char == 'q':
            break
            
    print("\n--- 錄製完成 ---")
    print("請將以下序列複製給我：")
    print(" -> ".join(sequence))
    print("----------------\n")

if __name__ == "__main__":
    recorder()
