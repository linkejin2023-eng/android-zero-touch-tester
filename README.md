# Android Sanity Test Automation 🤖

[![Python](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/)
[![Android](https://img.shields.io/badge/Android-15-green.svg)](https://www.android.com/)
[![UIAutomator2](https://img.shields.io/badge/UIAutomator2-Supported-orange.svg)](https://github.com/openatx/uiautomator2)

將 115 項傳統 OEM 手工 Android 視力與操作測試，轉化為 **82 秒全自動化、免接觸驗證** 的 Python 混合測試框架。專為無法 Root、鎖解鎖的 User Build 裝置所打造。

## 📊 專案總體進度 (Project Status)

![Progress](https://progress-bar.dev/60/?title=Overall&width=300)

| 開發階段 (Phase) | 狀態 | 進度百分比 | 包含模組與功能 | 最新更新日期 |
| :--- | :---: | :---: | :--- | :--- |
| **Phase 1: 核心框架與基底測試** | 🟢 完結 | **100%** | ADB 連線、螢幕控制、基礎音量控制 | 2026-03-06 |
| **Phase 2: 進階功能自動化** | 🟢 完結 | **100%** | 相機 Intent、WiFi/BT連網、觸控模擬、NFC、GPS | 2026-03-06 |
| **Phase 3: 使用者增強功能測試** | 🟡 進行中 | **0%** | 藍牙掃描清單、相機 JPG 存檔驗證、手電筒控制 | (開發中) |
| **Phase 4: 深水區硬體與穩定性** | ⏳ 企劃中 | **0%** | WWAN (有/無 SIM 卡判定)、麥克風錄音、MP4 影片解碼、系統重啟穩定性 | (企劃中) |
| **Phase 5: 企業級派發與 CI/CD** | ⏳ 企劃中 | **0%** | Email 總結報告發送、失敗日誌 (Logcat) ZIP 打包、重試機制 | (企劃中) |
| **Feature: AOAv2 OOBE 盲打POC** | ⏳ 企劃中 | **0%** | 透過 USB 虛擬鍵盤解除 Setup Wizard 限制 | (研究完畢) |

---

## 🚀 專案亮點 (Highlights)
1.  **100% 免接觸 (Zero-Touch) 軟體驗證**：不再需要人員手動滑動螢幕或確認指示燈，全程由腳本替代眼與手。
2.  **自動化 HTML 報告與發布建議**：一鍵產生清楚的綠/紅 Pass 表單，並基於成敗給出 `Release Recommendation`。
3.  **Setup Wizard 突破性研究**：詳載了如何在封閉的系統內，透過 AOAv2 HID 協定進行合法軟體控制的破解思路。

## 📖 目錄與技術文檔 (Documentation)
所有的設計細節、技術突破與測試覆蓋範圍，皆詳載於 `docs/` 資料夾下：

*   💡 [**測試框架設計 (ARCHITECTURE.md)**](docs/ARCHITECTURE.md) - 解釋結合 ADB System Level 與 UIAutomator 的混合層次驗證策略。
*   📋 [**自動化涵蓋範圍與策略 (TEST_COVERAGE.md)**](docs/TEST_COVERAGE.md) - 詳細列出 29 項測試的方法轉換，如何把物理動作變為軟體指令。
*   🔥 [**終極突破：零觸控 OOBE (ZERO_TOUCH_OOBE.md)**](docs/ZERO_TOUCH_OOBE.md) - 深入探討為何選擇 AOAv2 協定作為 Setup Wizard 封鎖下的唯一純軟體解答。

## ⚡ 快速開始 (Quick Start)
1.  **環境準備**：請確認測試機已透過 USB 連接至電腦，且已手動開啟「開發者選項」中的「USB 偵錯」。
2.  **安裝依賴**：
    ```bash
    pip3 install -r requirements.txt
    ```
3.  **執行測試**：
    ```bash
    python3 main.py
    ```
4.  **查看報告**：執行完畢後，HTML 測試報告將自動產生於 `reports/` 目錄中。
