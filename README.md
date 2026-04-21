# Android Smoke Test Automation (T70)

[![Python](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/)
[![Android](https://img.shields.io/badge/Android-15-green.svg)](https://www.android.com/)
[![UIAutomator2](https://img.shields.io/badge/UIAutomator2-Supported-orange.svg)](https://github.com/openatx/uiautomator2)

將 115 項傳統 OEM 手工 Android 視力與操作測試，轉化為 **82 秒全自動化、免接觸驗證** 的 Python 混合測試框架。專為無法 Root、鎖解鎖的 User Build 裝置所打造。

## 專案總體進度 (Project Status)


| 開發階段 (Phase) | 狀態 | 進度百分比 | 包含模組與功能 | 最新更新日期 |
| :--- | :---: | :---: | :--- | :--- |
| **Phase 1: 核心框架與基底測試** | 完結 | **100%** | ADB 連線、螢幕控制、基礎音量控制 | 2026-03-06 |
| **Phase 2: 進階功能自動化** | 完結 | **100%** | 相機 Intent、WiFi/BT連網、觸控模擬、NFC、GPS | 2026-03-06 |
| **Phase 3: 使用者增強功能測試** | 完結 | **100%** | 藍牙掃描清單、相機 JPG 存檔驗證、手電筒控制 | 2026-03-10 |
| **Phase 4: 深水區硬體與穩定性** | 完結 | **100%** | WWAN、音訊熵值分析、相機動態快門、OOBE Bypass、電源還原邏輯 | 2026-03-26 |
| **Phase 5: 企業級派發與 CI/CD** | 完結 | **100%** | Email 專業彙整報告、Fail-Safe 診斷機制、China SKU 整合 | 2026-04-16 |
| **Feature: 自動化燒錄 (Flash) 模組** | 完結 | **100%** | 支援 ZIP 自動解壓、Fastboot 流程與燒錄後自動接續 OOBE | 2026-03-12 |
| **Feature: 多 SKU (GMS/China) 支援** | 完結 | **100%** | 實作自適應 Branching 序列，支援 SIM/No-SIM 雙場景自動 OOBE Bypass | 2026-04-16 |
| **Phase 6: 跨電腦部署與相容性** | 完結 | **100%** | 實作 Portable Python 3.11 部署方案、本地指令自動偵測與 venv 隔離 | 2026-03-18 |
| **[T70] Phase 1: 核心架構與守門員規則** | 完結 | **100%** | Security Check、Config 控制、Baseline 核驗 | 2026-03-27 |
| **[T70] Phase 2: 演算法與穩定度優化** | 完結 | **100%** | Sensor 熵值分析、GPS 弱訊號、視力報表翻新 | 2026-03-27 |
| **[T70] Phase 2.1: 硬體強韌化** | 完結 | **100%** | 三段式硬體快門、自動解鎖 (Lock Screen Bypass) | 2026-03-27 |
| **[T70] Phase 3: 資料生命週期與收尾** | 完結 | **100%** | SKU Mapping、Legacy 清除、UserData 擦除 | 2026-04-02 |
| **[T70] Phase 4: 資料驅動全自動驗證 (Data-Driven)** | 完結 | **100%** | JSON 屬性自適應、混合提取引擎 (shell/logcat/ui)、免寫 Code 新增韌體測項 | 2026-04-02 |
| **[T70] Phase 5: 架構解耦與連線強韌化** | 完結 | **100%** | 執行 configs/ 目錄分離、WiFi/NFC/WWAN 強韌化、螢幕狀態自動還原 | 2026-04-02 |
| **[T70] Phase 6: CI 通知工業化** | 完結 | **100%** | 模組化專業通知、環境假失敗豁免邏輯 (Honest Exit Code) | 2026-04-16 |
| **[T70] Phase 7: 工業級加固與自癒機制** | 完結 | **100%** | 全路徑 INFRA_ERROR 報警、Factory Reset 劫持防護、智慧清理、預覽工具 | 2026-04-21 |

---

## 專案亮點 (Highlights)
1. **100% 免接觸 (Zero-Touch) 軟體解鎖**：領先業界實作鎖定畫面自動偵測與盲打解鎖，確保測試不因裝置休眠而中斷。
2. **音訊/感測器「生存」驗證**：透過方差與熵值 (Entropy) 數學模型，在靜止狀態下精確判定麥克風與加速度計硬體存活。
3. **三段式相機快門策略**：優先發動硬體鍵值 (Keyevent 27)，具備跨 App 版本的極高維護性與相容性。
4. **自動化 HTML 報告與發布建議**：一鍵產生清楚的綠/紅 Pass 表單，並基於 Smoke Test 成敗給出 `Release Recommendation`。

## 目錄與技術文檔 (Documentation)
所有的設計細節、技術突破與測試覆蓋範圍，皆詳載於 `docs/` 資料夾下：

* [**測試框架設計 (ARCHITECTURE.md)**](docs/ARCHITECTURE.md) - 解釋結合 ADB System Level 與 UIAutomator 的混合層次驗證策略。
* [**自動化涵蓋範圍與策略 (TEST_COVERAGE.md)**](docs/TEST_COVERAGE.md) - 詳細列出 29 項測試的方法轉換，如何把物理動作變為軟體指令。
* [**終極突破：零觸控 OOBE (ZERO_TOUCH_OOBE.md)**](docs/ZERO_TOUCH_OOBE.md) - 深入探討為何選擇 AOAv2 協定作為 Setup Wizard 封鎖下的唯一純軟體解答。
* [**版本紀錄 (CHANGELOG.md)**](CHANGELOG.md) - 詳細紀錄工業級加固的所有修復與優化細節。
* [**現狀與藍圖 (STATUS.md)**](STATUS.md) - 紀錄目前的穩定狀態與二代 Python 主控架構的發展規劃。

## 快速開始 (Quick Start)

### 1. 環境準備
- 請確認測試機已透過 USB 連接至電腦。
- **免 Sudo 權限設置** (僅需執行一次)：
 ```bash
 bash hid_gadget/setup_permissions.sh
 # 執行後請重新拔插 USB 線以生效
 ```

### 受限環境部署 (推荐方案)
針對舊版系統 (Python 3.6) 或無法全域安裝指令的受限環境，推薦使用 **Portable Python** 方案：

1. **取得現代引擎**：
 ```bash
 # 下載 Python 3.11 Standalone 引擎
 wget "https://github.com/astral-sh/python-build-standalone/releases/download/20240107/cpython-3.11.7%2B20240107-x86_64-unknown-linux-gnu-install_only.tar.gz" -O cpython-3.11-portable.tar.gz

 # 解壓至專屬目錄
 mkdir -p ~/python
 tar -xvf cpython-3.11-portable.tar.gz -C ~/python --strip-components=1
 ```
2. **建立虛擬環境**：
 ```bash
 ~/python/bin/python3 -m venv .venv
 source .venv/bin/activate
 pip install -r requirements.txt
 ```
3. **指令自動適配**：本工具會自動優先偵測 `backup_image/` 資料夾內的 `fastboot` 指令，無需手動配置系統 PATH。

---

---
### 2. CLI 範例 (Common Scenarios)

#### 情境 A: 標準測試 (裝置已在 Home Screen 且開啟 ADB)
```bash
python3 main.py --only-tests
```

#### 情境 B: China SKU 全自動 (燒錄 + 中國版 OOBE + 執行測試)
```bash
python3 main.py --flash /path/to/fastboot.zip --sku china
```

#### 情境 C: 僅繞過 OOBE (不燒錄，僅執行 AOA 盲打與 ADB 授權)
```bash
python3 main.py --oobe-only --sku china
```

#### 情境 D: 遠端 CI 觸發 (由 Jenkins/SSH 發動)
```bash
python3 trigger_job.py --build 20260421 --type user --source daily --remote-path /path/to/fastboot.zip
```

## CI/CD 整合結構 (Integration Architecture)

本專案實作了 **Build Server -> Test Server** 的閉環自動化流程，腳本依據執行環境分類如下：

### 1. Build Server 側 (`ci-integration/build_server/`)
存放於該目錄下的腳本負責調度編譯流程與觸發遠端測試：
- **`releasebuild_v2.bash`**: GMS Release 核心主控，負責修改版本號、觸發測試與發送精英級郵件。
- **`dailybuild_v2.bash`**: GMS Daily 核心主控，具備動態日期回傳機制。
- **`china_dailybuild_v2.bash`**: **[NEW]** China SKU Daily 主控，具備環境豁免與 NoGMS 通知特化。
- **`china_releasebuild_v2.bash`**: **[NEW]** China SKU Release 主控，支援深度 UNC 目錄路徑 (release/) 轉義。
- **`auto_release_*.bash`**: Release 版本編譯子腳本 (Worker)。
- **`auto_daily_*.bash`**: Daily 版本編譯子腳本 (Worker)。

> [!TIP]
> **防呆機制**：上述腳本均已導入 `SCRIPT_DIR` 自動定位邏輯，支援從任何工作路徑執行（例如 `bash ci-integration/build_server/releasebuild_v2.bash`），會自動尋找鄰近模板並產出 Artifacts。

### 2. Test Server 側 (專案根目錄)
負責接收指令並執行實際的硬體燒錄與功能驗證：
- **`trigger_job.py`**: **測試接收入口**，由 Build Server 透過 SSH 呼叫。
- **`main.py`**: 測試框架核心，由 `trigger_job.py` 調度執行。

### 3. 狀態判定權威檔案 (`configs/status_logic.yaml`)
該設定檔定義了每個測試項目的「影響等級」，決定了測試失敗時，整份報告會呈現什麼顏色與狀態（此顏色指報表頂端總結與郵件主旨的標籤顏色）：

| 等級 (Level) | 說明 | 報表顏色 | 對 Pass Rate 的影響 |
| :--- | :--- | :---: | :---: |
| **CRITICAL** | 致命錯誤（如連線中斷）。若失敗，主旨標記為 `[FAILED]`。 | 紅色 | 計入失敗 |
| **PARTIAL** | 一般功能失敗。若失敗，主旨標記為 `[PARTIAL]`。 | 黃色 | 計入失敗 |
| **ENV_EXCLUDED** | **環境/基礎設施因素**（如無 SIM 卡導致 WWAN 失敗）。 | 黃色 | **不計入**（視為豁免） |

> [!NOTE]
> 透過修改此 YAML 檔案，你可以「免寫代碼」直接調整某個測試項目是否應該阻礙 Release。例如：若實驗室環境暫時無法測試 GPS，可將 GPS 設為 `ENV_EXCLUDED`，避免其拖累總通過率。

---

### 3. CI 調度中心 (`trigger_job.py`)
這是 Jenkins/SSH 遠端觸發的核心進入點，負責搜尋 Image、搬運、執行與回傳。

#### 核心參數說明
- **`--build <ID>`**: 
  - **Daily**: 使用日期時間戳記 (例如 `202604210433`)。
  - **Release**: 使用正式版本號。**[智慧匹配]**：支援簡短版本號 (例如輸入 `02.01.06` 可自動匹配 `REL_02.01.06.N.260310`)。*注意：輸入的字串將直接決定 Workspace 與報表的命名。*
- **`--source <daily|release>`**: 指定搜尋來源目錄。
- **`--type <user|userdebug>`**: 指定編譯類型（預設為 `user`）。
- **`--remote-path <path>`**: **[重要]** 若提供此參數，系統將跳過搜尋，直接使用該路徑的 Image。支援遠端 Share 路徑或 Test Server 本地路徑。
- **`--sku <gms|china>`**: 指定產品 SKU（預設為 `gms`）。
- **`--check-only`**: (Optional) 僅進行連線、路徑與磁碟空間檢查，不執行實際燒錄與測試。

#### 使用範例

**情境 A: 遠端 CI 自動化模式 (由 Build Server 透過 SSH 發動)**
這是 CI 管道的最常用模式，透過帶入 Image Server 的絕對路徑來觸發：

```bash
# 1. GMS Release 範例 (完整版本號模式)
python3 trigger_job.py --build 02.01.06.260308 --type user --source release --remote-path /media/share/thorpe/Android_15/Release_pega/REL_02.01.06.260308/user/fastboot.zip

# 2. GMS Daily 範例 (時間戳記模式)
python3 trigger_job.py --build 202604210433 --type user --source daily --remote-path /media/share/thorpe/Android_15/dailybuild/202604210433_thorpe_user/fastboot.zip

# 3. China Release 範例 (包含 .N. 特徵)
python3 trigger_job.py --build 02.01.06.N.260310 --type user --source release --sku china --remote-path /media/share/thorpe/Android_15/Release_pega/REL_02.01.06.N.260310/user/fastboot.zip
```

**情境 B: 本地手動 Debug 模式 (Image 已在 Test Server 本地)**
如果你手邊已有 Image ZIP 並想跑一次完整流程（包含自動重置與 OOBE），可以直接帶入本地路徑：
```bash
# 執行本地 Image 測試
python3 trigger_job.py --build 99999 --type userdebug --source daily --remote-path /home/franck/test_images/fastboot.zip

# 測試完成後，執行預覽工具查看信件發送預期
python3 preview_notification.py
```

---

### 4. 參數說明 (main.py)
- `--flash <path>`: 指定燒錄包路徑，支援自動解壓縮（自動銜接 `--oobe`）。
- `--oobe`: **全自動流程**：啟動 OOBE 盲打流程並在完成後接著跑測試。
- `--oobe-only`: **僅執行整備**：跑完 OOBE 盲打與 ADB 授權後立即停止（適用於手動 Debug）。
- `--sku <gms|china>`: 指定產品 SKU（預設為 `gms`）。會切換不同的 OOBE 盲打序列。
- `--skip-tests`: 僅執行燒錄與 OOBE 解除，不執行功能測試。
- `--only-tests`: 略過所有整備流程，直接在現有桌面執行測項。
- `--config-dir <path>`: 指定配置目錄，優先讀取該目錄下的 `build_info.json`。
- `--report-dir <path>`: 指定 HTML 報表輸出目錄 (預設為 `reports/`)。
- `--build <version>`: 指定編譯版本（用於報表命名）。**[手動測試可省略，自動從機台偵測]**
- `--type <user|userdebug>`: 指定編譯類型。**[手動測試可省略，自動從機台偵測]**

### 5. 智慧郵件預覽工具
在正式發送 CI 通知前，可以使用預覽工具檢查信件格式與路徑判定：
```bash
python3 preview_notification.py
```
該工具會讀取 `test_summary.json` 並自動辨識 GMS/China 與 Daily/Release 模板。

### 6. 查看報告
- **主動執行**：報告產生成於 `reports/`。
- **SSH 觸發**：報告產生成於 `workspaces/完整版本號_type/report/`。
- **智慧清理**：系統會保留最近 4 份測試（保留份數可於 `configs/monitor_config.yaml` 的 `max_retention_zips` 修改），清理時會刪除巨大的 ZIP 與解壓資料夾，但精確保留 `report/` 與 `artifacts/` 以供回溯。
