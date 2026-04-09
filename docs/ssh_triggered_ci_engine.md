# SSH-Triggered Sanity Test Engine (No-Mount 版本)

將自動化測試功能轉型為由外部系統（如 Jenkins/Build Server）透過 SSH 主動觸發的任務引擎。本版本採用 **Rsync-over-SSH** 技術，無需網路掛載即可進行高效 Image 搬運。

## 系統架構簡述

- **觸發方式 (Triggering)**：
  外部系統執行以下指令啟動測試：
  `ssh <user>@<ip> "cd /path/to/auto_test/ && ./venv/bin/python3 trigger_job.py --build <build_num> --type <type> --source <daily|release> --sku <gms|china> > /dev/null 2>&1 &"`

- **傳輸方式 (Transfer)**：
  採用 `rsync` 透過 SSH 隧道從 Image Server 拖取檔案。支援斷點續傳與自動校驗，解決了傳統 SCP 斷線需從頭開始的問題。

- **環境依賴 (Prerequisites)**：
  1. 測試機須具備 `rsync` 工具。
  2. 測試機須已將其 SSH Public Key 加入 Image Server 的 `authorized_keys` 以實現免密碼傳輸。

## 主要功能

### 1. 無掛載設計 (No-Mount Design)
- 移除對 `/mnt/image_share` 的依賴。
- 透過 SSH 遠端命令 (`ls -d`) 動態偵測 Image Server 上的目錄結構，實現 Release 與 Daily 的模糊匹配。

### 2. 強韌的搬運機制 (Robust Transfer)
- 使用 `rsync --partial` 指令。
- 腳本具備指數型退避 (Exponential Backoff) 的重試邏輯，若傳輸中斷會自動重連並從中斷點續傳。

### 3. 工作空間隔離 (Workspace Isolation)
- 每次測試建立獨立 `workspaces/{build_num}_{type}/` 目錄。
- 保留最新 2 份 `fastboot.zip` 並無限期保留執行日誌與測試報表。

### 4. 阻塞式任務排隊 (Queuing)
- 採用檔案鎖機制。若設備正在執行測試，後續請求會自動排隊等待，確保資源不衝突。

---

## 檔案結構說明

- `trigger_job.py`: 核心調度腳本。
- `monitor/logic.py`: 遠端目錄讀取與 SKU 解析邏輯。
- `configs/monitor_config.yaml`: 定義遠端 Host、User 與基礎路徑。
- `framework/lock_manager.py`: 阻塞式鎖定實作。

