# 專案當前狀態 (Project Status)

## 最後更新
2026-03-27 18:30

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
 - 透過 GNSS_KPI 解析 SNR，實現室內弱訊號硬體驗證。
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
 - 配置優化：移除冗餘的 `lifecycle` 模組，統一由 `auto_factory_reset` 開關控制。
* [x] **[優先級 2] #7 SKU ID Mapping 優化**
 - 已實作於 `main.py`，支援 0x1112~0x1117 之硬體階段轉換。

---

### 第四階段：資料驅動驗證架構 (Data-Driven Verification)
 **全系統動態驗證已完結**

* [x] **[優先級 1] #9 Firmware 與 System Info 動態提取 (User Build 繞過)**
 - 徹底捨棄寫死的 Python 提取腳本，導入 `build_info.json` 作為單一真相來源。
 - 實作 `validations` 陣列解析，支援跨類別 (Build, Platform, Firmware) 驗證。
 - 針對 User Build 無法順利 `getprop` 的韌體與屬性，開發三型動態提取器 (Extractors)：
  1. **`shell` Extractor**: 執行原生 ADB Command (e.g. `getprop` / `uname -r`)
  2. **`logcat` Extractor**: 搭配 Regex 即時攔截 Kernel 或 System UI 印出的隱藏軟體版本
  3. **`ui` Extractor**: 自動化繞過 `Keyguard` 並導航 Settings 刮取特定選單 (`Built-in Keyboard`) 之 Summary 字串
* [x] **比對模式增強 (Matching Modes)**
 - 實作 `exact` 絕對匹配與 `contains` 包含匹配（完美對應 WWAN 版本具有隨機日期後綴的情境）。

---

### 總結結論
本專案已完成 **全系統無代碼 (No-Code) 屬性驗證擴充架構**。目前腳本已全數打通：
1. **自動解鎖** (Lock Screen Bypass)
2. **三項一體的混合提取引擎** (Shell/Logcat/UI)
3. **動態測試報告聯動** (JSON to HTML Report)

測試工程手只需維護 `build_info.json` 即可應對產線上萬變的韌體檢查需求，徹底解放系統環境！
