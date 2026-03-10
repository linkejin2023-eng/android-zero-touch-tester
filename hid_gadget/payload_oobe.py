import time

# HID Keyboard Modifier bitmasks
MOD_NONE = 0
MOD_LCTRL = 1 << 0
MOD_LSHIFT = 1 << 1
MOD_LALT = 1 << 2
MOD_LMETA = 1 << 3 # Windows/Command key

# USB HID Keycodes (A-Z: 4-29, 1-0: 30-39)
KEY_ENTER = 40
KEY_ESC = 41
KEY_BACKSPACE = 42
KEY_TAB = 43
KEY_SPACE = 44
KEY_RIGHT = 79
KEY_LEFT = 80
KEY_DOWN = 81
KEY_UP = 82

def send_key(hid_device, keycode, modifier=MOD_NONE):
    """Sends a single key press and release to /dev/hidg0."""
    # Press
    report = bytearray([modifier, 0, keycode, 0, 0, 0, 0, 0])
    with open(hid_device, 'rb+') as fd:
        fd.write(report)
    
    # Release
    null_report = bytearray([0, 0, 0, 0, 0, 0, 0, 0])
    with open(hid_device, 'rb+') as fd:
        fd.write(null_report)
        
    time.sleep(0.1) # Small delay to let Android UI catch up

def send_string(hid_device, text):
    """(Optional) Map character to HID keycode to type text."""
    # This is a simplified mapper. Only covers lowercase a-z and basic symbols.
    mapper = {
        'a': 4, 'b': 5, 'c': 6, 'd': 7, 'e': 8, 'f': 9, 'g': 10, 'h': 11,
        'i': 12, 'j': 13, 'k': 14, 'l': 15, 'm': 16, 'n': 17, 'o': 18,
        'p': 19, 'q': 20, 'r': 21, 's': 22, 't': 23, 'u': 24, 'v': 25,
        'w': 26, 'x': 27, 'y': 28, 'z': 29,
        ' ': KEY_SPACE, '\t': KEY_TAB, '\n': KEY_ENTER
    }
    
    for char in text.lower():
        if char in mapper:
            send_key(hid_device, mapper[char])
        time.sleep(0.05)

def bypass_setup_wizard():
    print("Starting Setup Wizard bypass sequence in 5 seconds...")
    print("Ensure device is plugged in and sitting on the 'Welcome/Hi There' screen.")
    hid_device = '/dev/hidg0'
    time.sleep(5)
    
    print("1. Sending Windows/Home key just in case it's not on first page...")
    send_key(hid_device, 0, MOD_LMETA)
    time.sleep(2)
    
    print("2. Tabbing to 'Start' and pressing Enter...")
    for _ in range(5):
        send_key(hid_device, KEY_TAB)
        time.sleep(0.5)
    send_key(hid_device, KEY_ENTER)
    time.sleep(3)
    
    print("\n*Note: Setup wizard UI varies GREATLY between Android versions and OEMs.")
    print("This payload is a generic placeholder. You will likely need to adjust the")
    print("number of TABs and ENTERs based on your specific device's ROM.*")
    print("\nPayload finished.")

if __name__ == '__main__':
    bypass_setup_wizard()
