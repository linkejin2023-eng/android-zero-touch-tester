import os
import subprocess
import logging

def parse_sku_from_build(build_number, source_type):
    """
    依據版本號命名規則判斷 SKU。
    """
    if source_type == "release":
        if ".N." in build_number:
            return "china"
    elif source_type == "daily":
        if "_nogms" in build_number:
            return "china"
    return "gms"

def get_full_build_name(build_number):
    """
    確保 Release 版本號包含 REL_ 前綴。
    """
    if not build_number.startswith("REL_") and not any(x in build_number for x in ["daily", "dev", "user"]):
        return f"REL_{build_number}"
    return build_number

def get_remote_dirs(host, user, base_path, pattern):
    """
    透過 SSH 取得遠端伺服器上的目錄列表。
    """
    # 確保路徑結尾有斜槓，並直接構建萬用字元字串
    if not base_path.endswith('/'):
        base_path += '/'
    search_path = f"{base_path}*{pattern}*"
    
    # 構建單一指令字串，避免 list 傳參時的 shell 解析差異
    cmd = ["ssh", f"{user}@{host}", f'ls -d {search_path} 2>/dev/null']
    
    logging.info(f"DEBUG: Remote search command: {' '.join(cmd)}")
    try:
        output = subprocess.check_output(cmd, text=True)
        results = [line.strip() for line in output.split("\n") if line.strip()]
        logging.info(f"DEBUG: Found remote dirs: {results}")
        return results
    except subprocess.CalledProcessError:
        return []
    except Exception as e:
        logging.error(f"Error listing remote dirs: {e}")
        return []

def find_source_zip(config, build_number, build_type, source_type, sku=None, remote_path=None):
    """
    尋找遠端伺服器上的 Image 與 Config。
    如果傳入 remote_path，則跳過搜尋，直接以該路徑為準 (IoC 模式)。
    回傳字典: { 'zip_path': str, 'json_path': str, 'full_build_name': str }
    """
    remote = config.get('remote_server', {})
    host = remote.get('host')
    user = remote.get('user')
    
    if not host or not user:
        logging.error("Remote server config missing.")
        return None

    if remote_path:
        # --- IoC 模式：直接解析傳入的絕對路徑 ---
        logging.info(f"CI-Injected mode: Using provided path {remote_path}")
        zip_abs_path = remote_path
        # 從絕對路徑中推算 target_dir (版本目錄)
        # 例如: .../REL_02.01.06/user/fastboot.zip -> .../REL_02.01.06
        if source_type == "release":
            target_dir = os.path.dirname(os.path.dirname(zip_abs_path))
        else:
            target_dir = os.path.dirname(zip_abs_path)
            
        full_build_name = os.path.basename(target_dir.rstrip('/'))
        json_dir = os.path.dirname(zip_abs_path.replace(target_dir, "").lstrip('/'))
        json_abs_path = os.path.join(target_dir, json_dir, "build_info.json")
    else:
        # --- 傳統模式：模糊搜尋 ---
        if source_type == "release":
            project_root_remote = remote.get('release_root')
            pattern = get_full_build_name(build_number)
        else:
            project_root_remote = remote.get('daily_root')
            pattern = build_number

        matching_dirs = get_remote_dirs(host, user, project_root_remote, pattern)
        
        # SKU 過濾
        if sku == "china":
            matching_dirs = [d for d in matching_dirs if (".N." in d or "_nogms" in d)]
        elif sku == "gms":
            matching_dirs = [d for d in matching_dirs if (".N." not in d and "_nogms" not in d)]

        if not matching_dirs:
            return None
            
        target_dir = sorted(matching_dirs, reverse=True)[0]
        full_build_name = os.path.basename(target_dir.rstrip('/'))
        
        if source_type == "release":
            zip_rel_path = os.path.join(build_type, config.get('fastboot_filename', 'fastboot.zip'))
        else:
            zip_rel_path = config.get('fastboot_filename', 'fastboot.zip')

        zip_abs_path = os.path.join(target_dir, zip_rel_path)
        json_dir = os.path.dirname(zip_rel_path)
        json_abs_path = os.path.join(target_dir, json_dir, "build_info.json")
    
    return {
        "zip_path": f"{user}@{host}:{zip_abs_path}",
        "json_path": f"{user}@{host}:{json_abs_path}",
        "full_build_name": full_build_name
    }

def get_workspace_dir(base_ws_dir, build_number, build_type):
    """
    產生專屬於當次任務的工作空間目錄。
    """
    safe_name = build_number.replace("/", "_")
    dir_name = f"{safe_name}_{build_type}"
    return os.path.join(base_ws_dir, dir_name)

def get_flash_command(main_py_path, zip_path, sku):
    """
    產生呼叫 main.py 的指令。
    """
    import sys
    cmd = [sys.executable, main_py_path, "--flash", zip_path]
    if sku == "china":
        cmd.extend(["--sku", "china"])
    return cmd
