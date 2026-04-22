# Changelog

## [2.2.3] - 2026-04-22
### 流程工業化 (Workflow Industrialization)
- **導入 Antigravity 技能系統**：建立 `.agent/skills/before-push/` 工作流，將「文檔保護」、「進度核對」與「提交流程」標準化為 AI 技能。
- **Git 忽略規則優化**：在 `.gitignore` 中新增 `.agents/` 排除規則，防止大型 AI 快取檔案干擾倉庫，並確保關鍵技能腳本被納入控管。
- **文檔保護協議升級**：在技能手冊中明文禁止對大型文檔進行全量覆寫，改採局部精確替換策略，徹底杜絕歷史遺失風險。

---


## [2.2.2] - 2026-04-21
### 核心架構加固 (Industrialization)
- **CI/CD 通知鏈條升級**：
  - 新增 [CRITICAL: INFRA_ERROR] 報警機制，覆蓋「Image 缺失」、「搬運失敗」、「設備斷線」等基礎設施故障。
  - 新增 [SUCCESS (Exempted)] 標籤，精確區分「純軟體成功」與「環境豁免項目」。
  - 實現 trigger_job.py 全路徑報警覆蓋，徹底杜絕「靜默失敗」。
- **路徑辨識演算法修正**：解決了正式環境下 Image Server 遠端路徑被誤判為本地路徑的關鍵 Bug。
- **Workspace 智慧清理**：
  - 保留數量提升至 4 份。設定位於 configs/monitor_config.yaml。
  - 自動清除巨大的 fastboot 資料夾與 .zip，但精確保留 report 與 artifacts 以供回溯。

### 測試穩定性優化 (Stability)
- **Factory Reset 防劫持機制**：
  - 新增 Google Maps 強制關閉與導航修正邏輯，解決了 GPS 測試殘留導致的重置失敗。
  - 將導航滑動上限從 10 次提升至 15 次，增加 50% 容錯空間。
- **遠端執行環境自癒**：修正了 SSH 遠端執行時找不到 fastboot 指令的崩潰問題，改為智慧警告並繼續執行。

### 開發與維護工具 (Tooling)
- **智慧郵件預覽工具 (preview_notification.py)**：支援 GMS/China、Daily/Release 四種模板自動辨識。
- **CI 腳本全線同步**：完成 GMS 與 China SKU (Daily/Release) 共四支主控腳本的邏輯對齊。
- **報表渲染修正**：修正 report_generator.py 的讀取 Key，確保 ENV_EXCLUDED 狀態能正確顯示為黃色標籤。

---


所有關於本專案的顯著變更將會記錄於此檔案中。

## [2.6.0] - 2026-04-16 - CI 工業化與 China SKU 深度整合 (CI Industrialization)
### Added (新增)
- **Release 全體系「模板自動化」整合**：
    - **支援 GMS 與 China SKU**：主控端現在會自動讀取原始模板，透過 `sed` 改版號後產出 `_v2` 檔案執行。
    - **自動發信靜默化**：`sed` 會自動註解子腳本內的所有 `mutt` 指令，確保郵件通知由 V2 主控端統一管理。
    - **SCM 友好介面**：維護者只需在主控端修改 `VERSION` 變數即可一鍵改版，不需進入子腳本。
- **Worker 腳本命名規範 (Naming Convention)**：
    - 保留原始 `auto_..._nogms_A15.bash` 不動。
    - 建立 `auto_..._nogms_A15_v2.bash` 作為增強版，實作時間戳同步與發信邏輯清理，對齊 GMS 精英版架構。
- **智慧型環境豁免邏輯 (Honest Exit Code)**：在 `main.py` 中導入 `SOFT_FAILURE_LIST` (GPS/NFC/WiFi)，確保退出碼誠實反映軟體品質。
- **精英級模組化通知郵件**：
  - **專業主旨格式**：`[SUCCESS/STABLE/FAILURE]` 狀態標籤、Variant 首字母大寫 (User/Userdebug)、以及 SKU/版號資訊。
  - **提貨連結優先**：郵件內文第一行即為軟體提取連結，大幅提升開發者獲取 Build 的效率。
- **深度 UNC 路徑修正**：針對 China SKU 特有的 `release/` 分支目錄結構，實作了精確的 Windows UNC 反斜線轉義邏輯。

### Changed (變更)
- **CI 調度架構統一**：GMS 與 China 流程對齊，共用相同的標題模板與路徑計算邏輯。
- **通知邏輯解耦**：移除所有 4 個原始 NoGMS 編譯腳本中的舊版 `mutt` 發信邏輯，徹底解決重複發信與格式混亂問題。
- **Daily Build 時間戳同步**：子腳本現在優先採用主控端導出的 `DATE_TAG`，保證通知連結與實體目錄 100% 匹配。


## [2026-04-15] - 工業級診斷強化與 Userdebug 深度支援 (Industrialization & Userdebug)
### Added (新增)
- **Userdebug 全面優化**：修復 AOA 驅動 VID/PID (05c6:901d)，解決 Userdebug 機台 OOBE 超時問題。
- **智慧型報表命名**：報表名稱現在會自動從及時 ID 中提取版本號，並聰明地避開 `release-keys` 等標籤。
- **跨版本異步郵件通知**：整合 `dailybuild_v2.bash`，實現待所有並行測試任務（User/Userdebug）結束後，發送單一彙整報告郵件。
- **深度硬體診斷**：報表頂部新增兩欄式診斷區，記錄 OEM Lock、SELinux、當前 Root 身分與 SKU 詳細資訊。
- **後門偵測機制**：區分「ADB Root 身分」與「系統 su 檔案」，精準捕捉工廠後門開啟狀態。
- **CLI 新選項**：新增 `--oobe-only`（純整備不測試）與 `--build/--type` 的自動偵測邏輯。

### Changed (變更)
- **安全預檢嚴格化**：針對 User build 恢復「零容忍」權限檢查，確保測試環境符合發布規範。
- **快速通道 OOBE**：若偵測到 ADB 已獲授權（如 Userdebug），則跳過 HID 模擬點擊，執行速度提升約 40 秒。

## [2026-04-14] - CI-Integration 結構化遷移與路徑防呆優化 (Deployment Optimization)
### Added (新增)
- **CI 專屬目錄化**：建立 `ci-integration/build_server/` 資料夾，將 Build Server 側的 Orchestration 腳本與編譯範本集中管理。
- **Daily Build 自動化閉環**：實作 `dailybuild_v2.bash`，導入「動態日期回傳 (Path Return Handshake)」機制，解決 Daily build 與 Test Server 之間因時間戳動態變化導致的路徑對接問題。
- **Bash 路徑防呆機制 (SCRIPT_DIR)**：在所有 CI 腳本（`releasebuild_v2.bash` 與 `dailybuild_v2.bash`）中導入 `SCRIPT_DIR` 自動定位邏輯，解決相對路徑對 PWD 的依賴，支援跨目錄呼叫。
- **混合部署指引**：在 `README.md` 中新增架構章節，明確區分 Build Server 與 Test Server 的腳本分工。

### Changed (變更)
- **腳本遷移**：遷移 `releasebuild.bash` (V1/V2) 及 `auto_daily/release_*` 腳本至新目錄，保持根目錄純淨，僅留測試核心。
- **Artifacts 管理**：優化 `LOCAL_ARTIFACT_DIR` 定位邏輯，確保建置產物穩定的產出於腳本鄰近目錄。

### Added (新增)
- **產物回傳 (Handback) 閉環**：測試結束後自動將報告同步回 Image Server 的版本目錄 (`test_reports/`)。
- **動態報表命名**：報表檔名現在包含 Model, Version 與 Variant (例如 `T70_smoke_test_report_02.02.01_user_*.html`)。

### Changed (變更)
- **全面品牌化更名**：將全系統的「Sanity Test」更名為「Smoke Test」，報表標題同步更換為「System Smoke Test Report」。
- **進入點控制流升級**：`main.py` 與 `trigger_job.py` 新增元數據傳遞支援。

## [2026-04-13] - 控制反轉與路徑注入 (IoC & Path Injection)
### Added (新增)
- **CI 注入路徑模式 (IoC Architecture)**：實作由 CI 腳本主動提供 Image 絕對路徑的機制，徹底解耦測試引擎與 Image Server 的目錄搜尋邏輯。
- **trigger_job.py 支持 `--remote-path`**：新增路徑注入參數，優先級高於自動模糊搜尋，符合「主管要求：Image path 由 CI 提供」的架構規範。
- **releasebuild_v2.bash 安全路徑計算**：在編譯端即時計算事實來源路徑 (Source of Truth)，確保測試數據的高度一致性。

## [2026-04-10] - 專業級 SSH 觸發式 CI/CD 引擎 (Rsync-over-SSH V2)
### Added (新增)
- **無掛載 Rsync-over-SSH 架構**：全面取代不穩定的本地掛載模式，改用 `rsync -av --partial -e ssh` 進行 Image 搬運，具備斷點續傳能力。
- **專業化 Workspace 管理**：自動讀取遠端伺服器元數據，使用「完整目錄名」（如 `REL_02.01.06.260308_user`）建立獨立工作空間。
- **動態配置同步機制**：實作即時從 Image Server 提取版本專屬 `build_info.json` 並注入 Workspace，實現配置與執行數據的完整隔離。
- **工業級安全觸發器 (Safe-Fail)**：
  - 新增 `releasebuild_v2.bash`，採用背景執行與錯誤隔離機制，確保自動化測試的失敗不影響編譯主流程。
  - 實作單一變數控制（Single Source of Truth），簡化週末正式發布的操作難度。
- **秒級驗證模式 (`--check-only`)**：為 `trigger_job.py` 新增核驗模式，可在 10 秒內完成 SSH 權限、遠端路徑與 Workspace 建立的端到端測試。

### Changed (變更)
- **測試框架路徑適配**：`main.py` 現在支援 `--config-dir` 與 `--report-dir` 參數，實現將所有產物（如 HTML 報表）精確收納至 Workspace。

### Removed (移除)
- **舊版 Polling 監控組件**：刪除過時的單機輪詢腳本 (`build_monitor.py`, `engine.py`, `worker.py`) 以維持原始碼整潔。

## [2026-04-02] - 架構解耦與連線強韌化 (Architecture & Stability)
### Added (新增)
- **設定檔精確解耦**：將 `build_info.json` 遷移至 `configs/` 目錄，並依據工作職掌拆分為 `build_info.json` (版本與驗證)、`hardware_specs.json` (硬體參數) 與 `ui_selectors.json` (UI 字典)。
- **NFC 強韌偵測**：實作 30s 輪詢 (Polling) 機制與 `logcat -c` 自動清理，解決實體 Tag 貼附感應失敗問題。
- **螢幕狀態管理**：新增測試前自動喚醒 (Wakeup) 與解鎖 (Unlock) 功能，並實作電源狀態「備份與還原」機制，確保測試結束後還原用戶原始休眠設定。

### Changed (變更)
- **WiFi 連線強韌化**：將連線超時延長至 90s，並導入 `ip addr` 現代指令與 RSSI/Link Speed 即時診斷日誌，解決遠距離連線不穩。
- **韌體提取穩定性**：針對 WWAN/Baseband 加入 3 次指數後退重試 (Retry with Backoff)，解決 RIL 啟動初期讀取失敗。
- **報告引擎修補**：修正測試耗時 (Duration) 為 0 的問題，導入自動增量計時器與 Header 總耗時顯示。

 
## [2026-04-01] - 資料驅動驗證架構 (Data-Driven Verification)
### Added (新增)
- **通用設定檔驅動 (`build_info.json`)**：徹底移除 Python 代碼中寫死的 `getprop` 與 UI 驗證邏輯，改由 JSON 動態載入 `validations` 陣列，實現「免寫 Code 即可新增測項」的終極目標。
- **混合型萃取引擎 (Hybrid Extractors)**：
 - `shell`：負責快速屬性抓取 (e.g. `ro.build.version.release`)
 - `logcat`：負責攔截特定系統日誌 (e.g. 觸控 IC 韌體)
 - `ui`：負責深度選單導航、自適應點擊與防呆滾動 (e.g. 實體鍵盤韌體)
- **多重比對模式**：支援 `exact` 與 `contains` 比對模式，完美適應具有 Timestamp 尾綴的韌體版本（如 WWAN 模組）。

### Changed (變更)
- **UI 提取強化與防呆**：
 - 在所有 `ui` 驗證前，加入更強韌的 `wm dismiss-keyguard` 結合實體 `Swipe` 解鎖，確保裝置脫離休眠態。
 - 引入多層級錯誤捕捉 (Exception Handling)，UIAutomator 找不到元素時不再崩潰，而是優雅回報 `Not found` 並自動擷取 XML Dump 到隨身碟供除錯。

### Removed (移除)
- **硬編碼測試指令**：移除了 `firmware_expectations.yaml` 與 `test_firmware.py` 內舊有僵化的 if-else 邏輯陣列。
 
## [2026-03-27] - 視力介面翻新與核心基座完結 (Infrastructure & Optimization)
### Added (新增)
- **UI 報表全面儀表板化 (Visual Dashboard Refresh)**：徹底改寫 `framework/report_generator.py`，導入 Donut Chart、子系統進度條與 SKIP/ERROR 狀態追蹤，無需外部 JS 依賴。
- **自動化裝置解鎖 (Auto-Unlock)**：在測試啟動前自動偵測鎖定狀態，透過 `wm dismiss-keyguard` 與 AOSP 滑動模擬達成 100% 盲打解鎖。
- **核心架構模組化 (Infrastructure Refactoring)**：引入 `config.yaml` 實現模組開關與參數抽離，並實作 `baseline.yaml` 用於韌體版本權威核驗。
- **Gatekeeper 安全檢查機制**：在 `main.py` 啟動前強制執行 SELinux Enforcing 與非 Root 驗證，實現 Fail-Fast 操作。

### Changed (變更)
- **三段式快門觸發結構**：針對 Task D 優化目標，將 `test_camera.py` 重構為「Keyevent 優先 -> UI 降級輔助 -> 座標保底」結構，徹底解決 UI 改版失效問題。

### Fixed (修正)
- **Sensor 靈敏度判定 (平行任務 A)**：引入方差/標準差運算 (Variance)，實現對加速度計與陀螺儀的熵值分析，精確區分「休眠 (Sleep)」與「損壞 (Fixed Value)」。
- **GPS/GNSS 寬容判定 (平行任務 B)**：新增 T70 專用 `GNSS_KPI` 解析器，支援在室內弱訊號下的硬體驗證。
- **WiFi 連線強韌化 (平行任務 C)**：移除對掃描快取的依賴，強制執行連線指令並優化 IP 獲取等待邏輯。
- **報告完成度匯總**：修復了 `main.py` 在特定環境下遺漏模組結果的統計錯誤。

## [2026-03-26] - 音訊熵值分析與相機動態適配 (T70 穩定化)
### Added (新增)
- **音訊硬體熵值分析 (Audio Entropy Analysis)**：針對 OS 封鎖併發放音的限制，改用位元組隨機性分析 (Unique Byte Count)，實現 100% 自動化麥克風硬體存活驗證。
- **相機動態快門適配**：自動偵測螢幕解析度並動態計算快門座標，解決特定解析度下的 UI 點擊偏移問題，並改用 `find -mmin` 提升檔案偵測可靠性。

### Fixed (修正)
- **電源狀態自動還原**：在測試結束後（無論成功失敗）自動將「保持喚醒 (Stay Awake)」設為 OFF，恢復正常休眠行為。
- **ADB 指令提示機制**：當使用者誤在 OOBE 畫面使用 `--only-tests` 時，提供引導式錯誤訊息。

### Removed (移除)
- **鬧鐘測試 (Set Alarm)**：移除 `test_housekeeper.py`，因其在無外部解碼器下缺乏閉環驗證。

## [2026-03-25] - 通用 OOBE Bypass 與相機錄影穩定化
### Added (新增)
- **通用 GMS OOBE Bypass**：實作自適應分支重試邏輯，支援「有插 SIM 卡」與「沒插 SIM 卡」的自動跳轉，並具備自動 Reset 功能。
- **權威式相機錄影驗證**：捨棄不穩定的檔案系統輪詢，改用 Logcat 提取系統級儲存路徑 (`printFileName`)，徹底解決幽靈檔案 Mis-hit 問題。

### Added (新增)
- **SKU ID 匯報**：報告標頭現在會自動讀取並顯示 `ro.boot.sku` (例如 `0x1114`)。
- **重啟穩定性性能測試 (`test_reboot.py`)**：自動執行 `adb reboot` 並精確測量系統恢復至 `sys.boot_completed` 的耗時與校正後的 Kernel Uptime。
- **連線開關功能性驗證**：在 `test_connectivity.py` 中新增 WiFi 與 Bluetooth 的「關閉狀態」驗證，確保開關不僅是 UI 變化而是確實中斷連線。

### Fixed (修正)
- **連線判定強韌化**：為應對 Trimble T70 介面殘留 `UP` 旗標的特性，優化了 WiFi/BT 關閉後的判定邏輯，改以 `settings` 狀態與 IP 消失作為權威判定標準。
- **相機錄影誤判**：修復了 Snapcam 暫存檔導致的 FAIL 問題，加入多重降級 (Fallback) 偵測機制。
- **音訊權限跳過**：更新了 `test_audio.py` 的 OOBE 循環，支援更多客製化隱私通知視窗的自動點擊。

### Removed (移除)
- **非確定性與無法物理驗證測項移除**：刪除了「觸控 (Touch)」、「音量鍵 (Buttons)」、「強迫關機 (Force Shutdown)」、「螢幕亮度」、「開關螢幕」、「LED 燈」與「手電筒」。
 - **理由**：這些項目在全自動環境下缺乏「軟體層面」的閉環驗證，若無外部攝影機觀測，無法 100% 斷定物理狀態（如螢幕是否真的變暗），改為手工物理測試以確保自動化報表的權威性。

## [2026-03-18] - 受限環境部署驗證與指令偵測優化
### Fixed (修正)
- **ADB/Fastboot 偵測邏輯優化**：修復了當系統未安裝 adb/fastboot 分別時，誤將「command not found」報錯訊息識別為 Android 裝置的 Bug。
- **偵測精準度提升**：改用嚴格的序號 (Serial) 正則匹配，確保連線狀態判斷 100% 正確。

### Changed (變更)
- **Portable Python 部署方案正式驗證**：確認在 Python 3.6+ 之舊版或受限環境中，透過 Standalone Python 3.11 引擎可完全打通自動化測試流程。
- **本地指令優先機制**：`FlashManager` 現在會自動偵測並優先使用燒錄包內建的 `fastboot` 二進制檔，大幅降低環境依賴。

## [2026-03-13] - 架構優化、多 SKU 支援與受限環境部署規劃
### Added (新增)
- **多 SKU 支援正式實作**：
 - 引進 `--sku <gms|china>` 參數，動態切換 AOA HID 盲打序列。
 - 實作 China SKU (NAL) 專用 OOBE 跳過邏輯與 ADB 授權路徑調校。
- **受限環境部署規劃 (進行中)**：
 - 生成 `requirements.txt` 與環境診斷工具 `check_env.py`。
 - 撰寫 `deployment_plan.md` 與安全性評估報告。
 - **Legacy Compatibility**：規劃將核心代碼回溯至 Python 3.6+ 相容語法以適應特定受限環境。

### Changed (變更)
- **旗標邏輯修正**：優化 `--skip-tests` 邏輯，解決手動除錯模式下的 ADB 超時報錯。
- **README 更新**：加入虛擬環境 (venv) 初始化說明與多 SKU 指令範例。

## [2026-03-12] - 自動化燒錄流程整合與穩定性達成
### Added (新增)
- **自動化燒錄模組 (`FlashManager`)**：實作 ZIP 韌體包自動解壓與 Fastboot 燒錄流程。
- **燒錄與 OOBE 連接**：支援在燒錄完成後自動轉入 AOA HID 盲打模式。

### Changed (變更)
- **系統權限調校**：移除 `flash_manager` 內的 `sudo` 依賴，改用 `udev` 規則管理權限。
- **ADB 監控優化**：在授權成功後立即結束 PID 切換等待。

## [2026-03-11] - 基礎 Sanity 測試框架完結
### Added (新增)
- 完成 29+ 台手機功能測試自動化（包含：相機、通訊、音訊、感測器等）。
- 自動化 HTML 測試報告生成引擎。
