# SSH-Triggered Sanity Test Engine (V2 - No-Mount / Rsync-over-SSH)

本系統支援由外部 CI/CD 平台（如 Jenkins 或特定伺服器）透過 SSH 主動觸發測試任務。V2 版本全面改為 **Rsync-over-SSH** 傳輸，不僅符合「無掛載 (No-Mount)」的安全政策，更實現了 Workspace 的專業化管理。

## 核心特色 (V2 升級)

- **無感網路掛載 (Zero-Mount Dependency)**：不再需要預先部署掛載點，降低伺服器維護成本。
- **Workspace 對齊 (Identity Sync)**：測試目錄名稱自動對齊 Image Server 上的完整版本名（例如 `REL_02.01.06.260308_user`），優化數據回溯。
- **動態配置同步 (Dynamic Build Info)**：自動從 Image Server 抓取該版本對應的 `build_info.json`。
- **斷點續傳 (Partial Transfer)**：採用 `rsync --partial`，在不穩定網路下具備自動重連補傳能力。

## 觸發方式 (Triggering)

在外部伺服器執行以下指令（需已配置 SSH 免密碼）：

```bash
ssh <user>@<測試機IP> "cd /home/franck_lin/auto_test/ && ./.venv/bin/python3 trigger_job.py --build <版本號> --type user --source release --sku gms --remote-path <絕對路徑>"
```

### 參數說明 (trigger_job.py)
- `--build`: 欲測試的版本號（如 `02.01.06`）。系統會自動模糊搜尋並匹配遠端最合適的完整目錄。
- `--type`: 指定版本類型 (`user` / `userdebug`)。
- `--source`: 指定目錄來源 (`release` / `daily`)。
- `--sku`: 指定產品 SKU (`gms` / `china`)。
- `--remote-path`: **[V2.2 核心升級]** 由外部注入的絕對路徑。當提供此參數時，系統將跳過目錄搜尋，符合 IoC (Inversion of Control) 原則，消除了測試機與伺服器結構的依賴。
- `--check-only`: **[V2.1 新增]** 僅執行連線、路徑與資料夾建立核驗，不進行傳輸，用於快速驗證流水線。

## 工作空間結構 (Workspace Structure)

每次測試會建立獨立的 Workspace，其結構如下：

```text
workspaces/REL_02.01.06.260308_user/
├── console.log            # 任務執行完整日誌
├── fastboot.zip           # 下載的燒錄包
├── build_info.json        # [V2] 從遠端抓取的該版本專屬規格檔
├── report/                # [V2] 該次測試產生的 HTML 報表
│   └── sanity_report_xxx.html
└── artifacts/             # [V2] 預留存放截圖、Logcat 等附加產物
```

## 系統架構簡述

1. **偵測與注入階段**：`trigger_job.py` 優先接收來自 CI Script 注入的 `--remote-path`。若未提供，則透過 SSH 掃描 Image Server 上的目錄（模糊搜尋模式）。
2. **同步階段**：使用 `rsync` 提取 `fastboot.zip` 與 `build_info.json` 至 Workspace。
3. **執行階段**：啟動 `main.py` 並傳入 `--config-dir` 與 `--report-dir` 參數，確保測試引擎只讀取動態同步的配置，並將產物回寫至 Workspace。
4. **清理階段**：根據 `max_retention_zips` 策略自動清理過期的 Image 包，但保留文字日誌與報表。

## 環境依賴 (Prerequisites)

1. 測試機須具備 `rsync` 工具。
2. 測試機須具備 Image Server 的 **SSH 免密碼** 權限：
   `ssh-copy-id -i ~/.ssh/id_rsa.pub <remote_user>@10.192.188.16`

