import logging
import time
from framework.adb_helper import run_adb_cmd
from framework.ui_automator import UIHelper

def run_tests(ui: UIHelper, reporter, validations=None):
    """
    Runs multi-module firmware verification with comparison against JSON expectations.
    """
    logging.info("Running Multi-Module Firmware Verification (Data-Driven)...")
    validations = validations or []
    
    if not validations:
        logging.warning("No firmware validations provided in configuration.")
        return

    for val_item in validations:
        category = val_item.get("category", "Firmware")
        name = val_item.get("name", "Unknown Component")
        expected = str(val_item.get("expected", ""))
        mode = val_item.get("mode", "exact")
        extractors = val_item.get("extractors", [])
        
        logging.info(f"Checking {name} using mode '{mode}'...")
        
        actual_val = None
        for extractor in extractors:
            try:
                logging.info(f"Attempting extraction via: {extractor.get('type')}")
                actual_val = execute_extractor(ui, extractor)
                if actual_val:
                    logging.info(f"Extracted value: {actual_val} via {extractor.get('type')}")
                    break
            except Exception as e:
                logging.warning(f"Extractor {extractor.get('type')} failed for {name}: {e}")
        
        compare_and_report(reporter, category, name, actual_val, expected, mode)

def execute_extractor(ui: UIHelper, extractor):
    ext_type = extractor.get("type")
    
    if ext_type == "shell":
        cmd = extractor.get("command")
        _, out = run_adb_cmd(cmd)
        out = out.strip()
        if not out:
            return None
        if extractor.get("split_by"):
            parts = out.split(extractor.get("split_by"))
            idx = extractor.get("split_index", 0)
            if len(parts) > abs(idx) or (idx == -1 and len(parts) > 0):
                return parts[idx].strip()
        return out

    elif ext_type == "logcat":
        cmd = extractor.get("command")
        _, out = run_adb_cmd(cmd)
        if not out.strip():
            return None
            
        if extractor.get("split_by"):
            parts = out.split(extractor.get("split_by"))
            idx = extractor.get("split_index", -1)
            if len(parts) > 0:
                return parts[idx].strip()
        return out.strip()

    elif ext_type == "ui":
        run_adb_cmd("input keyevent KEYCODE_WAKEUP")
        time.sleep(1)
        run_adb_cmd("input keyevent 82")
        run_adb_cmd("wm dismiss-keyguard")
        run_adb_cmd("input swipe 500 1000 500 100") # Swipe to unlock
        time.sleep(1.5)

        run_adb_cmd("am force-stop com.android.settings")
        time.sleep(1)
        
        intent = extractor.get("intent")
        run_adb_cmd(f"am start -a {intent}")
        time.sleep(3)
        
        clicked = True
        if "click_texts" in extractor:
            clicked = False
            for text in extractor["click_texts"]:
                if ui.d(text=text).exists:
                    ui.d(text=text).click()
                    clicked = True
                    break
        if not clicked and "click_pattern" in extractor:
            pat = extractor["click_pattern"]
            target = ui.d(textMatches=pat)
            if not target.exists:
                try: ui.d(scrollable=True).scroll.to(textMatches=pat)
                except: pass
            target = ui.d(textMatches=pat)
            if target.exists:
                target.click()
                clicked = True
            else:
                clicked = False
                
        if ("click_texts" in extractor or "click_pattern" in extractor) and not clicked:
            return None
            
        if clicked and ("click_texts" in extractor or "click_pattern" in extractor):
            time.sleep(1)
        
        target = None
        if "target_text" in extractor:
            lbl = extractor["target_text"]
            if not ui.d(text=lbl).exists:
                try: ui.d(scrollable=True).scroll.to(text=lbl)
                except: pass
            target = ui.d(text=lbl)
        elif "target_pattern" in extractor:
            pat = extractor["target_pattern"]
            if not ui.d(textMatches=pat).exists:
                try: ui.d(scrollable=True).scroll.to(textMatches=pat)
                except: pass
            target = ui.d(textMatches=pat)
            
        val = None
        if target and target.exists:
            summary = target.sibling(className="android.widget.TextView", resourceId="android:id/summary")
            if summary.exists():
                val = summary.get_text()
            else:
                try:
                    val = target.info['text'].split(':')[-1].strip()
                except Exception as e:
                    run_adb_cmd("uiautomator dump /sdcard/fw_debug.xml")
                    run_adb_cmd("pull /sdcard/fw_debug.xml .")
                    pass
        else:
            run_adb_cmd("uiautomator dump /sdcard/fw_fail_debug.xml")
            
        run_adb_cmd("am start -c android.intent.category.HOME -a android.intent.action.MAIN")
        return val

    return None

def compare_and_report(reporter, category, name, actual, expected, mode):
    if not actual:
        reporter.add_result(category, name, False, "Not found")
        return

    actual_str = actual.strip()
    expected_str = expected.strip()
    
    is_pass = False
    if mode == "exact":
        is_pass = (actual_str == expected_str)
    elif mode == "contains":
        is_pass = (expected_str in actual_str)
    else:
        is_pass = (actual_str == expected_str) 

    if is_pass:
        reporter.add_result(category, name, True, actual_str)
    else:
        msg = f"MISMATCH! Actual: {actual_str}, Expected ({mode}): {expected_str}"
        reporter.add_result(category, name, False, msg)
        logging.error(f"Validation Mismatch for {name}: {msg}")
