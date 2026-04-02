# 專案當前狀態 (Project Status)

## 最後更新
2026-04-02 18:30

## 待執行開發清單 (Next Deliverables)
 
### 第一階段：核心架構與守門員規則 (Infrastructure & Gatekeepers) 
 **全案基座已完結**
 
* [x] **[優先級 1] #10 安全權限檢查 (Security & Root Check)**
 - 實作於 `main.py` 的 Preflight Check，確保 SELinux Enforcing 與非 Root 環境。
* [x] **[優先級 2] #1 測試模組化與 Config 控制**
 - 實作 `config.yaml` 抽離 SSID/密碼與模組開關。
* [x] **[優先級 3] #2 韌體版本權威核驗 (baseline.yaml)**
 - 抽離版本驗證邏輯，提升測試報告之權威性。
 
### 第二階段：演算法與穩定度優化 (Test Logic Optimization)
 **效能優化與強韌化已完結**
 
* [x] **UI 報表全面翻新 (Visual Dashboard Refresh)**
 - 改寫 `framework/report_generator.py`，導入 Donut Chart 與子系統進度條。
 - 支援 SKIP/ERROR 狀態追蹤與無痛版本相容。
 
* [x] **[平行任務 A] #4 Sensor 靜態熵值分析**
 - 引入方差/標準差運算，精確區分「休眠」與「固定值故障」。
* [x] **[平行任務 B] #3 GPS 弱訊號判定優化**
 - 透過 GNSS_KPI 解析 SNR，實作室內弱訊號硬體驗證。
* [x] **[平行任務 C] #6 連線互斥檢查機制**
 - 使用 `ip route` 與 `ifconfig` 確保路由表純淨，已驗證 100% 互斥。
* [x] **[平行任務 D] #11 UI 觸發策略優化** (Camera/Audio)
 - 已將 UI 點擊降級為輔助，優先發動 `adb shell input keyevent`。

---

### 第三階段：資料生命週期與收尾 (Lifecycle & Cleanup)
 **生命週期與儲存核驗已完結**

* [x] **[優先級 1] #5 Factory Reset 全自動驗證閉環 (Full Cycle)**
 - 實作「重置 -> AOA 重新繞過 OOBE -> 再次稽核」的完整流程。
 - 報告優化：將驗證結果濃縮至 **System** 分類，顯示 Uptime 與檔案數量的變化對比。
* [x] **[優先級 2] #7 SKU ID Mapping 優化**
 - 支援 0x1112~0x1117 之硬體階段轉換。

---

### 第四階段：資料驅動驗證架構 (Data-Driven Verification)
 **全系統動態驗證已完結**

* [x] **[優先級 1] #9 Firmware 與 System Info 動態提取 (User Build 繞過)**
 - 導入 `configs/build_info.json` 作為單一真相來源。
 - 針對 User Build 開發三型動態提取器 (Extractors)：`shell`, `logcat`, `ui`。
* [x] **比對模式增強 (Matching Modes)**
 - 實作 `exact` 絕對匹配與 `contains` 包含匹配。

---

### 第五階段：硬體數據與指令全面解耦 (Hardware & Command Decoupling)
 **專案已完結 (Completed)**

* [x] **[工作流優化] 設定檔依權責拆分**
 - 實作 `configs/build_info.json`：由軟體版本工程師維護預期值與提取邏輯。
 - 實作 `configs/hardware_specs.json` 與 `ui_selectors.json`：由自動化工程師維護硬體門檻與 UI 字典。

---

### 第六階段：測試強韌化與維護 UX (Stability & Reporting UX)
 **系統維護性與穩定性已達標**

* [x] **連線穩定性強化**：WiFi 延長超時 (90s) 並導入即時 RSSI 診斷。
* [x] **NFC 偵測準確率提升**：30s 輪詢機制結合 `logcat -c` 自動清理。
* [x] **報告引擎修補**：修正耗時顯示 (Duration bug) 並導入自動增量計時。
* [x] **電源生命週期保護**：測試前後自動備份與還原螢幕電源設定。

---

### 總結結論
本專案已完成 **100% 數據驅動之解耦架構**，實現了以下里程碑：
1. **測試邏輯與資料分離**：所有專案參數、路徑、介面名稱與 UI 定位器均已移出核心 Code base。
2. **具備「版控工程師」友好的工作流**：可獨立更新 FW 版本而無需接觸 Python。
3. **高強韌度的硬體感應**：針對 WiFi、NFC、WWAN 等不穩定因子均實作了重試與診斷機制。
