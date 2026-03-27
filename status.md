# 專案當前狀態

## 最後更新
2026-03-26 13:50

## 檔案說明
- 專案總體進度與快速開始請見：README.md
- 歷史變更紀錄請見：CHANGELOG.md
- 本檔案僅用於記錄「當下對話」的掛起任務，以便新開對話時能快速接軌。

## 🚀 待執行開發清單 (Next Deliverables)

1.  **測試模組化與 Config 控制**：
    -   實作一個外部 `config.yaml` 或 `test_config.json` 來決定哪些測項要執行（Enabled = true/false）。
    -   動態路徑控制：讓 SSID / Password 等敏感資訊從腳本中抽出，便於環境切換。
2.  **韌體版本權威核驗 (Firmware Baseline Check)**：
    -   **規格分析**：建議使用 **YAML** 格式 (`baseline.yaml`)，因其支援註解且對巢狀結構 (WWAN/Touch/Keypad) 友善。
    -   **實作**：讀取 `dumpsys` 或 `cat /sys/...` 的節點值，並與 Baseline 全字元比對，不一致則 FAIL。
3.  **GPS 弱訊號判定優化**：
    -   即使 `Fix` 不完全（不在窗邊），若 `Satellite Count > 0` 或 `SNR > 0` 則判定硬體收訊正常。
4.  **Sensor 靜態熵值分析**：
    -   仿照 MIC 的邏輯，對 Accelerometer / Gyro / Magnetometer 進行數值波動分析，確保即便放在桌上，數值也不是死掉的常數。
5.  **Factory Reset 完整性驗證**：
    -   在燒錄後或手動 Reset 後，檢查 `/sdcard/DCIM`, `/sdcard/Music`, `/sdcard/Pictures` 以及 Alarm 資料庫是否為空。
6.  **連線互斥檢查機制**：
    -   測試 WiFi 時，確認 `wwan0` 已關閉且無 Route。
    -   測試 WWAN 時，確認 `wlan0` 已斷開且無 Route。
7.  **SKU ID Mapping 優化**：
    -   報告中將 `0x1112` 對應為 `EVT`, `0x1113` 為 `DVT1` 等，方便閱讀。
8.  **燒錄跳過 UserData 擦除**：
    -   新增 `--no-wipe` 選項，模擬 OTA/使用者更新情境，保留現有檔案。
9.  **遺留代碼清除**：
    -   徹底刪除已廢止的 `test_display.py` 與 `Input Device Listing` 殘留邏輯。

10. **安全權限檢查 (Security & Root Check)**：
    -   在測試啟動前，檢查 `ro.debuggable`, `getenforce` (SELinux 狀態) 與 `su` 執行路徑。
    -   若偵測到 **Root** 或 **SELinux Permissive**，則視為不安全環境，立即中斷測試並回報錯誤；若正常，則將「SELinux: Enforcing」記錄在報告中。
11. **UI 觸發策略優化 (UI vs Keyevent)**：
    -   **問題**：Snapcam 或錄音 App 的 UI ID 可能隨系統更新變動，維護成本高。
    -   **優化方向**：評估將 `keyevent` (如 Camera:27) 作為「標準觸火方式」，並將 UI 偵測改為「輔助驗證」，確保腳本具備跨版本的高度相容性。
12. **uiautomator 具備性**：
    -   確認專案使用的是 AOSP 標準架構下的 `uiautomator2` 封裝，具備工業級穩定性。

## 🎯 階段性結論
本專案已完成從燒錄、OOBE、到各項核心硬體 (WiFi/BT/Cam/Mic/NFC/GPS) 的高強韌自動化驗證。
所有測項均符合「100% 軟體閉環」且「False-Positive Free」的設計目標。

## 接續指令
"請讀取 status.md 並接續新待辦項目的詳細開發。"
