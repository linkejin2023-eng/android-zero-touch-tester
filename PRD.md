# Android Sanity Test Automation - 產品需求與實現文檔 (PRD)

---

## 1. 專案背景與目標 (Project Background & Objective)
*   **目標**：將原先一份需要大量人工視力檢查與實體操作的 Android Sanity Test Report (共 115 項目)，轉化為 **100% 免接觸、全自動化執行**的 Python 測試腳本。
*   **預期效益**：將每次測試耗時從數十分鐘壓縮至 1~2 分鐘內，並自動產出 HTML 測試報告與 Release Recommendation（版本發布建議），有效抓出環境、軟體整合的退化 (Regression) 問題。
*   **目標硬體/軟體**：Trimble T70 機台，載有 Android 15 (User Build, locked bootloader)。

---

## 2. 目前已開發功能與實現進度 (Developed Features & Progress)
專案採階段性開發，目前已完成 **Phase 1 (核心基準) 與 Phase 2 (進階模組)**，總計 29 項關鍵測試點。

### 📊 第一階段 & 第二階段完成度：100%
此部分已在實機上驗證，無須人工介入即可**約在 82 秒內完成掃描**：
1.  **System / Framework**：自動 ADB 連線驗證、UIAutomator 後台守護進程自動注入與連線。
2.  **Display**：螢幕亮度調整 (Settings API)、實體電源鍵 Suspend (休眠) 與 Resume (喚醒) 模擬及驗證。
3.  **Audio**：Audio Service 啟動狀態、Audio HAL 掛載檢查、Media Volume 調整控制與 `dumpsys audio` 提取。
4.  **Camera**：Camera HAL 可用性、App 前景啟動。且具備防呆機制，能自動透過 `pm grant` 處理權限對話框，或使用 UIAutomator 閃避 `settings.intelligence` 意圖選擇器 (Disambiguation Popup)。
5.  **Connectivity**：WiFi 開關、自動連線指定 AP 並等候 DHCP 配發 IP 驗證；Bluetooth 開關 (`bluetooth_on`) 狀態校驗。
6.  **Sensors / Power**：Accelerometer、Gyro、Light Sensor、e-Compass 驅動層狀態檢查 (`dumpsys sensorservice`)；電池電量讀取與 AC 拔插斷電事件模擬 (`dumpsys battery set ac 0`)。
7.  **Touchscreen**：觸控 Input Device 列舉檢查 (`getevent -l` 對應)、四向滑動手勢 (Swipe / Drag) 模擬與 UI 回應校驗。
8.  **HouseKeeper / System App**：LED 指示燈狀態檢查 (`dumpsys lights`)、發送鬧鐘設定 Intent 驗證。
9.  **Hardware Buttons**：長按 Power Key 呼叫電源選單 (Power Menu) 驗證、Keypad 實體按鍵 (數字 0-9、方向鍵、Del) 訊號路由 (Routing) 正確性。
10. **NFC & Location**：NFC 底層服務啟動校驗 (`svc nfc enable`)；GPS/GNSS Location Provider 註冊狀態檢查。

### 🔄 報告產出：
每個階段的結果都會被實時蒐集，自動編譯為一份帶有時間戳記的 `.html` 檔案 (例如 `sanity_report_20260306_100716.html`)，內含綠色/紅色清楚的 Pass/Fail 統計與細節紀錄。

---

## 3. 實現計畫 (Implementation Plan)
以 Python 為主要開發語言，基於主控端 (Host PC) 向 Android 發送控制與獲取反饋。

### 3.1 架構與設計模式
*   **混合驗證策略 (Hybrid Validation)**：結合 **ADB System Level (硬核打底)** 與 **UIAutomator (使用者視覺交互)**。
    *   *ADB*: 用於注入底層感測器讀取、切換網路、模擬按鍵、改變電池狀態等。
    *   *UIAutomator*: 用於解析畫面的 View Tree，確認 App 是否確實被打開、滑動是否生效、對話框是否正確被點擊關閉。
*   **模組化設計**：所有測試分類拆分成獨立模組 (例如 `test_camera.py`, `test_touch.py`)，由 `main.py` 統一排程執行。

### 3.2 後續第三階段計畫 (Phase 3 - User Enhancements)
針對使用者的回饋，預計開發以下增強項目：
1.  **藍牙掃描 (BT Scan)**：除了檢查開啟，還將進入藍牙設定頁面，驗證是否能掃描出「附近裝置清單」，確診藍牙天線功能。
2.  **手電筒 (Flashlight/Torch)**：拉下系統通知欄 (Quick Settings) 點擊手電筒開關並驗證系統節點，確認補光燈硬體運作。
3.  **相機實拍留存 (Camera Capture)**：不只啟動相機，要模擬按下快門 (`KEYCODE_CAMERA`)，並檢查 `/sdcard/DCIM/Camera` 內照片數量是否 +1 且大小 > 0。
4.  **實體鍵盤 (Keypad) 限制備註**：目前雖然做到 100% 免接觸，但 `input keyevent` 為軟體層注入。無法證實實體鍵盤背後的排線是否斷裂，這是純軟體測試無法企及的硬體層極限（除非結合治具）。

### 3.3 深水區硬體與穩定性 (Phase 4 - Deep Hardware)
為了無限逼近原生 115 項硬體涵蓋率，將針對特定硬體進行深度檢驗：
1.  **WWAN (行動上網模組)**：針對裝置特性，若未插 SIM 卡，腳本讀取 `dumpsys telephony.registry` 確認 Modem 模組/IMEI 存活；若插有 SIM 卡，則進階驗證 Carrier 名稱與訊號強度 (dBm)。
2.  **Audio Advanced (麥克風錄音)**：透過 `arecord` 錄製 3 秒環境音，確保麥克風與音效解碼正常。
3.  **Video Playback (MP4 影片硬解)**：播放系統或自定義的短影音，確保 Hardware Codec 無 System Crash。
4.  **Reboot Stability (系統穩定性)**：發出重啟指令，監聽裝置回連後檢查 `sys.boot_completed` 標籤與 `dropbox` 系統崩潰日誌。*(註：考量硬體現狀，已剔除 SD 卡與震動馬達測試。)*

### 3.4 企業級 CI/CD 與報告派發 (Phase 5 - Enterprise CI/CD)
將這套自動化從「單機腳本」升級為「企業級自動化測試管線」：
1.  **Auto-Delivery (Email SMTP 派送)**：腳本結束時不再只儲存於本地，而是將帶有 Pass/Fail/Release 建議的 HTML 報告自動寄發至指定信箱。
2.  **Failure Artifacts (現場還原)**：遇到錯誤當下，立馬執行 `adb bugreport` 擷取 Logcat 與螢幕截圖並打包成 `.zip` 附件，供工程師 Debug。
3.  **Flakiness Retry (防抖動重試)**：針對 Android UI 若因系統負載而卡頓導致誤判的測項，實施至多 3 次重跑機制。

---

## 4. 關鍵技術難點與突破：Setup Wizard (OOBE) 解局 🌟

### 4.1 挑戰背景
目標機器為 Android User Build（不可 root、不可解鎖 Bootloader 修改 OS），在每次重刷機 (Flashing) 之後，系統會進入「開機精靈 (Setup Wizard / OOBE)」。
在此階段，**USB 偵錯 (ADB) 預設為完全封鎖**。這導致原本期待的「PC 一接上就透過 ADB 全自動化」面臨雞生蛋、蛋生雞的死胡同。只能倚賴人員用手指一一點擊螢幕跳過 OOBE，並按七次版本標號打開 ADB 後，自動化腳本才能接手。

### 4.2 嘗試但被否決的方案
*   **修改 `build.prop` (`ro.setupwizard.mode=DISABLED`)**：違反「不修改 User Build 原生 OS」的原則，且需要解鎖 Bootloader。
*   **Android Enterprise QR Code Provisioning**：雖然可掃碼部署，但 AOSP 標準 payloads 內未提供「略過 OOBE 且強制打開 ADB」的直接參數。
*   **Linux USB Gadget API 模擬硬體解法 (UDC)**：欲將測試 PC 虛擬化成真正的 USB 鍵盤/滑鼠騙過手機，因測試機 (Dell XPS 筆電 Intel USB Controller) 硬體沒有 "Dual-Role / Device" 控制晶片 (UDC) 宣告失敗。
*   **藍牙 HID 模擬**：Setup Wizard 尚不支持無屏無密碼強制藍牙配對。

### 4.3 終極關鍵突破：AOAv2 HID 協定 (Android Open Accessory)
在探索 AOSP 內建的非標準、但合法授權的底層原始碼時，挖掘出極冷門卻外掛級的解法 —— **AOAv2 (Android Open Accessory Protocol 2.0)**。

*   **技術原理**：
    AOSP 設計 AOA 讓外部配件能控制手機。**AOAv2 具備 HID 支持能力**。他最核心的特徵是：能夠在 **Host (主機，即一般 PC)** 與 **Device (裝置，即 Android 手機)** 的標準角色不互換的情況下，強制 Android 進入 "Accessory Mode"。
*   **實現手段 (Zero-Touch 盲打後門)**：
    只要手機開機，插上普通的 USB Type-C 線。電腦端可撰寫 Python 腳本 (藉由 `pyusb`):
    1. 使用 USB Control Requests (Endpoint Zero) 發送 AOA Handshake，讓手機的 USB VID/PID 變成配件模式。
    2. 送出 `ACCESSORY_REGISTER_HID` 與鍵盤的 Report Descriptor，**把一般沒有 UDC 功能的電腦，當場變成一台專門伺候這台 Android 的虛擬鍵盤**。
    3. 送出 `ACCESSORY_SEND_HID_EVENT`。既然變成鍵盤了，就能全自動在黑屏或 OOBE 畫面狂塞 `Tab`、`Enter`、方向鍵。
    4. 腳本「盲打」跳過開機精靈，甚至一路點擊進入 `Settings`，點 7 下打開 `Developer Options` 並啟用 `USB Debugging`。
*   **突破結論**：
    上述方案不依賴特殊的 PC 硬體，也不需要外部微控制器 (如 BadUSB 或 RPi Pico)，是目前地球上能在**不改機的情況下，達成 100% 絕對純軟體解除 User Build OOBE 的唯一方案**。目前該方法處於概念驗證 (POC) 規劃階段，準備投入實機腳本演練 (`aoa_keyboard.py`)。
