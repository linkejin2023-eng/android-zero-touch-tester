# Security and Safety Assessment / 部署安全性評估

This document outlines the system-level interactions of the Sanity Test tool to ensure safe deployment on corporate domain machines.
本文件詳述測試工具與系統層級的互動，確保在公司網域電腦上部署的安全性。

## 1. System Changes (Host Computer) / 系統變更 (主機端)

### A. Udev Rules (`setup_permissions.sh`)
- **Action**: Creates `/etc/udev/rules.d/51-android-aoa.rules`.
- **Impact**: **Minimal & Safe**. It only tells the Linux kernel to allow non-root users to communicate with specific USB IDs (Trimble & Google).
- **Risk**: None. It does not affect other USB devices or system stability.
- **Action**: 建立 udev 規則檔案。僅針對特定 USB ID 開放讀寫權限，不影響其他硬體或系統穩定性。

### B. Python Environment / Python 環境
- **Action**: Recommended use of `venv` (Virtual Environment).
- **Impact**: **None**. All libraries (`pyusb`, `uiautomator2`) are isolated inside the project folder. Even without `venv`, it only installs standard PyPI packages.
- **Action**: 建議使用虛擬環境。所有依賴庫皆隔離在專案資料夾內，不會污染系統全域路徑。

### C. System Binary Paths / 系統路徑
- **Action**: Assumes `adb` and `fastboot` are in the `$PATH`.
- **Impact**: **None**. The tool uses the existing system tools; it does not install or replace them.
- **Action**: 使用現有的系統工具，不會替換或破譯原本的 ADB/Fastboot 二進位檔。

## 2. Hardware Interaction / 硬體互動

### A. HID Simulation (Keyboard/Mouse)
- **Action**: Uses AOAv2 to simulate a keyboard **ON THE PHONE**.
- **Impact**: **Safe**. It **DOES NOT** control the host computer's keyboard or mouse. Your computer remains fully operational while the script is typing on the phone.
- **Action**: 模擬的是「手機端」的輸入。不會干擾主機本身的鍵盤或滑鼠。

### B. Flashing Logic
- **Action**: Executes standard `fastboot flash` commands.
- **Impact**: Standard procedure for device testing. It only targets the connected USB device in fastboot mode.
- **Action**: 僅針對 Fastboot 模式下的 USB 裝置進行操作，具備標準燒錄風險（但在受控測試環境內）。

## 3. Data Privacy / 資料隱私
- **Internet Usage**: `uiautomator2` might check for updates or download a small `atx-agent` to the phone if missing.
- **Logs**: All logs and reports are stored locally in the `reports/` folder. No data is sent to external servers.
- **隱私**: 所有測試報告與日誌僅存放在本地 `reports/` 資料夾，不會上傳至任何外部伺服器。

## 4. Conclusion / 結論
The tool is **System-Safe**. The only administrative action required is the one-time `setup_permissions.sh` to handle USB permissions. Everything else runs in user-space with no risk of "breaking" the host OS.
本工具為 **系統安全**。唯一的管理員操作是初始的權限設置，其餘皆在使用者空間運行，無損壞 OS 環境之風險。
