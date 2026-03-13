import os
import zipfile
import subprocess
import logging
import time
from framework.adb_helper import wait_for_device

class FlashManager:
    """Manages the flashing process for Android devices."""

    def __init__(self, zip_path: str):
        self.zip_path = os.path.abspath(zip_path)
        self.extract_dir = os.path.dirname(self.zip_path)
        logging.info(f"FlashManager initialized with ZIP: {self.zip_path}")

    def extract_firmware(self) -> bool:
        """Extracts the firmware ZIP to its current directory."""
        try:
            logging.info(f"Extracting {self.zip_path} to {self.extract_dir}...")
            with zipfile.ZipFile(self.zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.extract_dir)
            logging.info("Extraction successful.")
            return True
        except Exception as e:
            logging.error(f"Failed to extract ZIP: {e}")
            return False

    def _run_local_cmd(self, cmd: str, cwd: str = "") -> tuple[int, str]:
        """Runs a local shell command and returns (exit_code, output_combined)"""
        try:
            logging.debug(f"Running: {cmd} (cwd='{cwd}')")
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                cwd=cwd if cwd else None
            )
            combined_output = (result.stdout + "\n" + result.stderr).strip()
            return result.returncode, combined_output
        except Exception as e:
            logging.error(f"Command Error: {e}")
            return -1, str(e)

    def wait_for_fastboot(self, timeout: int = 60) -> bool:
        """Waits for a device to be detected in fastboot mode."""
        logging.info(f"Waiting for Fastboot device (timeout={timeout}s)...")
        start = time.time()
        while time.time() - start < timeout:
            code, out = self._run_local_cmd("fastboot devices")
            if out.strip():
                logging.info(f"Fastboot device detected: {out.split()[0]}")
                return True
            time.sleep(2)
        logging.error("No Fastboot device found.")
        return False

    def flash(self) -> bool:
        """Executes the full flashing workflow."""
        # 1. Search for existing script first to skip extraction
        bash_script = None
        bash_dir = None
        for root, dirs, files in os.walk(self.extract_dir):
            if "fastboot.bash" in files:
                bash_script = os.path.join(root, "fastboot.bash")
                bash_dir = root
                break

        if bash_script:
            logging.info(f"Found existing flash script at: {bash_script}. Skipping extraction.")
        else:
            # 2. Extract if not found
            if not self.extract_firmware():
                return False
            # Search again after extraction
            for root, dirs, files in os.walk(self.extract_dir):
                if "fastboot.bash" in files:
                    bash_script = os.path.join(root, "fastboot.bash")
                    bash_dir = root
                    break

        if not bash_script:
            logging.error(f"Sanity Error: fastboot.bash not found anywhere in {self.extract_dir}")
            return False

        # 2. Check Connection
        logging.info("Checking if device is connected (ADB or Fastboot)...")
        in_fastboot = self.wait_for_fastboot(timeout=5)
        in_adb = wait_for_device(timeout=5) if not in_fastboot else False

        if not in_fastboot and not in_adb:
            logging.error("No device detected in ADB or Fastboot mode. Please connect the device.")
            return False

        # 3. Reboot to Bootloader (if needed)
        if in_adb:
            logging.info("Device in ADB mode, rebooting to bootloader...")
            self._run_local_cmd("adb reboot bootloader")
            if not self.wait_for_fastboot():
                return False
        else:
            logging.info("Device already in Fastboot mode.")
        
        # 4. OEM Unlock (Optional but usually needed)
        logging.info("Unlocking OEM: Trimble-Thorpe")
        code, out = self._run_local_cmd("fastboot oem unlock Trimble-Thorpe")
        if code != 0:
            logging.warning(f"OEM Unlock might have failed or already unlocked: {out}")

        # 6. Execute fastboot.bash
        logging.info(f"Executing flash script: {bash_script}")
        
        # Ensure script is executable
        self._run_local_cmd(f"chmod +x {bash_script}")
        
        # Ensure the 'fastboot' binary in the same directory is also executable
        fastboot_bin = os.path.join(bash_dir, "fastboot")
        if os.path.exists(fastboot_bin):
            self._run_local_cmd(f"chmod +x {fastboot_bin}")

        # Optimization: Remove 'sudo ' from the script internally to avoid 
        # interactive password prompts or environment issues. 
        # We do this even if not currently root, as long as udev rules are set.
        try:
            with open(bash_script, 'r') as f:
                content = f.read()
            if 'sudo ' in content:
                logging.info(f"Stripping 'sudo' from {os.path.basename(bash_script)} to prevent interactive hangs.")
                new_content = content.replace('sudo ', '') # Remove sudo from commands
                with open(bash_script, 'w') as f:
                    f.write(new_content)
        except Exception as e:
            logging.warning(f"Could not strip sudo from script: {e}")

        # START FLASHING
        logging.info("Starting flashing... (Note: Running without sudo, ensuring udev rules are set)")
        code, out = self._run_local_cmd(f"./fastboot.bash", cwd=bash_dir)
        
        if code != 0:
            logging.error(f"Flashing failed with exit code {code}. Detailed Output:\n{out}")
            return False
        
        logging.info("Flashing command executed successfully.")

        # 7. Reboot
        logging.info("Rebooting device...")
        self._run_local_cmd("fastboot reboot")

        logging.info("Fastboot reboot command sent. Returning to main to handle OOBE bypass.")
        return True
