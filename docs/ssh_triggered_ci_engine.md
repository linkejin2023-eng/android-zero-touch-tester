# SSH-Triggered Sanity Test Engine

將自動化測試功能轉型為由外部系統（如 Jenkins/Build Server）透過 SSH 主動觸發的任務引擎。具備工作空間隔離、多版本目錄匹配與阻塞排隊機制。

## 系統架構簡述

- **觸發方式 (Triggering)**：
  外部系統執行以下指令。建議配合 `nohup` 以防止 SSH 斷線導致任務中斷：
  `ssh <user>@<ip> "cd /path/to/auto_test/ && ./venv/bin/python3 trigger_job.py --build <build_num> --type <type> --source <daily|release> --sku <gms|china> > /dev/null 2>&1 &"`

- **環境需求 (Mounting)**：
  測試機必須預先將儲存伺服器掛載至 `/mnt/image_share`：
  `sudo mount -t cifs -o username=<U>,password=<P> //10.192.188.16/share /mnt/image_share`

## 主要功能

### 1. 工作空間隔離 (Workspace Management)
- 每次執行自動建立 `workspaces/{build_num}_{type}/` 目錄。
- 測試過程中所有的 `console.log`、報表與下載的 Zip 檔案皆限制在該目錄內，確保測試結果可追溯。

### 2. 多軌路徑與 SKU 解析 (Path Logic)
根據傳入的 `--source` 參數切換搜尋邏輯：
- **Release 模式**：
  - 路徑：`/mnt/image_share/thorpe/Android_15/Release_pega/REL_{build_num}*/{type}/fastboot.zip`
  - SKU 判定：若指令未指定，則規則為包含 `.N.` 則判定為 `china`。
- **Daily 模式**：
  - 路徑：自動搜尋 `/mnt/image_share/thorpe/Android_15/dailybuild/` 下包含 `build_num` 關鍵字的目錄。
  - SKU 判定：規則為包含 `_nogms` 則判定為 `china`。

### 3. 阻塞式任務排隊 (Queuing & Locking)
- 使用 `fcntl.flock` 的 **阻塞模式**。
- 當設備正在執行測試時，新的 SSH 觸發請求會自動進入等待狀態，直到前一個任務釋放鎖鎖定，實現「無遺漏」的接力執行。

### 4. 智慧清理機制 (Smart Cleanup)
- 測試完成後自動掃描 `workspaces/`。
- 保留最新 2 份 Workspace 內的 `fastboot.zip` 供緊急手動測試。
- 無限期保留文字類 Log 與 HTML 報表。

---

## 檔案結構

- `trigger_job.py`: CLI 進入點，負責調度、掛載點搜尋與任務執行。
- `monitor/logic.py`: 核心路徑匹配與 SKU 判定邏輯。
- `monitor/database.py`: SQLite 歷史紀錄管理。
- `framework/lock_manager.py`: 實作阻塞式檔案鎖。
- `configs/monitor_config.yaml`: 集中定義掛載路徑與清理策略。

