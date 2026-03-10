# 自動化涵蓋範圍與策略 (TEST COVERAGE)

本專案致力將原本 115 項目、需要大量人工視力檢查與實體操作的 Android Sanity Test Report，轉化為 **100% 免接觸、全自動化執行** 的 Python 測試腳本。

## 🎯 測試模組清單 (共計 29 項核心基準驗證)

目前測試涵蓋了 Phase 1 (基礎) 與 Phase 2 (進階) 的 29 個環節，所有腳本都能在 **82 秒內無人值守執行完畢**。以下是驗證手段從「實體動作」轉換為「軟體判讀」的策略大全：

### 1. 螢幕顯示與休眠 (Display)
*   **Set Brightness**: 改變背光設定 (`settings put system screen_brightness 50`) 並讀回驗證。
*   **Suspend & Resume**: 傳送電源鍵 (`input keyevent 26`) 模擬按下開關，並連續讀取 `dumpsys power` 確認 `mWakefulness` 狀態是否在 `Asleep` 與 `Awake` 間切換。

### 2. 音訊與喇叭 (Audio)
*   **Service & HAL**: 查驗作業系統是否有啟動音效伺服端進程，且 Audio HAL 是否被硬體正確掛載。
*   **Volume Control**: 寫入媒體音量變更，並從 `dumpsys audio` 確認是否真正傳達到作業系統設定中。

### 3. 相機功能 (Camera)
*   **HAL 初始化**: 確認底層系統列舉出至少一顆攝影鏡頭。
*   **App 啟動與防呆**: 發出 `am start -a android.media.action.IMAGE_CAPTURE` Intent 喚起相機。
    *   *突破點*：Android 系統常會彈出第一次使用的「權限詢問框」或擁有多個相機 App 的「選擇器 (Resolver)」，導致自動化卡死。本腳本實作了前置 `pm grant` 給予相機權限，並且在等待期間被動認可 `settings.intelligence` 的存在即視為通過（因為彈出選擇器就證明 Intent 發送成功）。

### 4. 網路與連線 (Connectivity)
*   **WiFi**: 傳送 `svc wifi enable` 啟動天線，連線至指定的 Access Point，並**靜候 15 秒等待 DHCP 原生取號**後，檢查 (`ip addr show wlan0`) 是否獲得真實內部 IP。
*   **Bluetooth**: 傳送 `svc bluetooth enable`，並向 Settings 查詢 `bluetooth_on` 全域變數以保障功能確實開啟。

### 5. 感測器與電源管理 (Sensors & Power)
*   **Acc / Gyro / Light Driver**: 無法實際「搖晃」機器，改由讀取 `dumpsys sensorservice` 來驗證驅動程式是否提供此硬體能力，並且確認服務活躍。
*   **Battery Status**: 從系統中抽出目前剩餘電量與充電模式。
*   **AC Unplug Simulation**: 發送 `dumpsys battery set ac 0` 欺騙系統充電線已拔除，驗證 Android 電源架構的事件處理與回應機制的健康度。

### 6. 觸控與操控 (Touchscreen)
*   **Input Device Listing**: 讀取原生 `/dev/input/` 子系統，找出 Touch 裝置。
*   **Multi-Direction Swipe**: 透過 UIAutomator 連續對畫面實施上下左右四個方向的滑動注入 (Swipe / Drag)，確保觸控框架回應且不卡頓。

### 7. 進階感測器與背景呼叫 (Advanced Sensors)
*   **e-Compass**: 確認磁力計驅動掛載。
*   **Game App Launch Test**: 測試跨越不同 Activity 的背景 APK 意圖觸發能力與狀態檢測。

### 8. 系統底層服務 (HouseKeeper)
*   **Alarm**: 透過系統 Intent `android.intent.action.SET_ALARM` 送出參數，驗證鬧鐘核心服務是否接手。
*   **LED**: 不使用 `/sys/class/leds/` (因 User Build 權限阻擋)，改為讀取 `dumpsys lights` 服務狀態，確認指示燈系統的通道是順暢的。

### 9. 實體按鍵配置 (Buttons / Keypad)
*   **Power Menu**: 模擬長按電源鍵 (`input keyevent --longpress KEYCODE_POWER`)，隨後用 UIAutomator 解析畫面上是否有彈出「Power off」的緊急關機選單。
*   **Keypad Mapping**: 連續注入 `KEYCODE_0`, `KEYCODE_1`, `KEYCODE_DEL` 等對應的實體按鈕訊號。
    *   *限制備註*：這驗證了 Android 軟體 Input Routing 正確運作，但「純軟體」無法隔空證實實體按鍵物理上的薄膜接點是否損壞。

### 10. 定位與通訊協定 (GPS & NFC)
*   **NFC**: 強制 `svc nfc enable` 後查扣服務對列，確認天線模組驅動。
*   **GPS**: 啟用 Location Manager 內的 GNSS Location Provider，確認搜星模組註冊無礙。

---

## 📅 未來排程 (Phase 3)
*   **Bluetooth Scan**: 擴建掃描功能，實質查找附近裝置數量以驗證藍牙天線健康度。
*   **Flashlight Torch**: 解析 Quick Settings 並控制手電筒。
*   **Camera JPG Capture**: 發送快門指令，並實體驗證 `/sdcard/DCIM/Camera` 有無正確寫出 JPG 圖片檔。

## 📅 未來排程 (Phase 4 - 深水區硬體與穩定性)
*   **WWAN (行動網路)**: 
    *   **無卡情境**: 透過 `dumpsys telephony.registry` 讀取 Modem 狀態與 IMEI，證明通訊模組晶片存活。
    *   **有卡情境**: 讀取電信商名稱 (Carrier) 與訊號強度 (dBm) 或連線狀態。
*   **Audio Advanced (麥克風錄音)**: 透過 `arecord` 指令或錄音 Intent 錄製一段背景音，並驗證產出的音訊檔大小大於 0。
*   **Video Playback (MP4 影片解碼)**: 推播 MP4 測試檔至手機並呼叫系統播放器，透過 `dumpsys media.player` 確認 Hardware Codec (硬體解碼器) 無崩潰。
*   **Reboot Stability (系統重啟穩定度)**: 腳本發送重啟指令，連線恢復後檢查 `sys.boot_completed` 標籤，並撈取 `dropbox` (系統崩潰日誌中心) 確保開機過程中無 System Server Crash。

## 📅 未來排程 (Phase 5 - 企業級派發與 CI/CD)
*   **Auto-Delivery (Email 派發)**: 測試執行完畢後，透過 SMTP 協定自動將 HTML 報告與摘要寄發給預設的 Email 聯絡群組。
*   **Failure Artifacts (現場還原包)**: 當面臨測試失敗 (Fail) 時，自動觸發 `adb bugreport` 或 `logcat`，擷取崩潰日誌與當下截圖，打包成 `.zip` 附件。
*   **Flakiness Retry (容錯重試機制)**: 針對偶發性的 UI 延遲或卡頓，實作最多重試 3 次的防抖動機制 (Debounce)，減少無效的警報。
