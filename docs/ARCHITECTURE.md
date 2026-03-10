# 測試框架設計與架構 (ARCHITECTURE)

本專案的核心挑戰在於：如何在 **「不可 Root、不可修改 Bootloader，且完全無人工觸控」** 的嚴苛條件下，驗證上百項硬體與軟體功能？
為此，我們設計了 **混合驗證策略 (Hybrid Approach)**，同時運用了底層系統指令與使用者視覺級別的自動化工具。

## 1. 混合式驅動：ADB System Level + UIAutomator

### 為什麼需要 ADB (Android Debug Bridge)?
ADB 是我們深入系統骨幹的「硬核打底」工具。許多測試項目無法依靠「看螢幕」來確認（例如感測器是否掛載），必須直接詢問作業系統核心服務。
*   **用途**：
    *   **狀態詢問**：透過 `dumpsys (sensorservice, audio, battery, lights)` 拿取最純粹的驅動或 HAL 層狀態。
    *   **強力注入**：發送特定 Intent (`am start`) 強制呼叫相機、設定頁面，或是發送 `input keyevent` 模擬實體按鍵（如電源鍵、數字鍵）。
    *   **權限迴避**：測試相機時，透過 `pm grant` 提前給予 App 全域權限，防止畫面被系統安全權限框 (Permission Dialog) 卡死。

### 為什麼需要 UIAutomator2 (Python)?
有些功能就算底層報告「正常」，如果 UI 卡住了或沒點擊成功，對使用者來說依然是壞的（例如觸控面板與 App 的交互）。這時我們需要「視覺查證」。
*   **用途**：
    *   **畫面對驗**：解析 Android 當下表層的 XML 結構 (View Tree)。可以直接辨識並點選 `text="Always"` 之類的按鈕。
    *   **手勢模擬**：與 ADB 呆板的 `input swipe` 不同，UIAutomator 可以確認目標 App 被拉到前景後，再進行細膩的滾動、點擊操作，並「看見」操作後畫面的變化是否符合預期。

> 💡 **黃金準則**：**「先用 ADB 打通任督二脈（權限、狀態），再用 UIAutomator 執行視覺與交互驗證。」**

---

## 2. 專案目錄與模組化設計

為了易於維護與擴展功能，整個專案採取高度模組化架構，由一個入口程式 `main.py` 進行統一的主排程。

```text
Sanity_Test/
├── main.py                  # 🚀 主控台：負責裝置連線、初始化報告庫、按順序呼叫所有 Test Modules
├── requirements.txt         # 📦 Python 依賴包 (utiautomator2, jinja2 等)
│
├── framework/               # 核心引擎與工具箱
│   ├── adb_helper.py        # 封裝所有的 subprocess `adb shell` 呼叫與錯誤處理
│   ├── ui_automator.py      # 管理 uiautomator2 agent 的連線與基礎輔助方法
│   ├── report_generator.py  # 負責蒐集所有模組的測試結果，並渲染輸出為 HTML 格式
│   │
│   └── tests/               # 🧪 獨立測試模組 (可隨意抽換、獨立執行)
│       ├── test_audio.py    # 音效、HAL、音量相關測試
│       ├── test_camera.py   # 相機前/後景色、儲存空間存取測試
│       ├── test_touch.py    # 觸控面板、多向滑動驗證
│       ├── test_gps.py      # 定位服務 Provider 驗證
│       └── ... (其餘 25+ 模組)
│
└── reports/                 # 📄 每次 `main.py` 跑完自動生成的 HTML 報告儲存區
```

### 開發者指南：如何新增一個測試？
若未來有新的硬體（例如指紋掃描）需要加入自動化，您只需要：
1.  在 `framework/tests/` 建立一個 `test_fingerprint.py`。
2.  在此檔案內實作 `def run_tests(ui: UIHelper, reporter: HTMLReportGenerator):`。
3.  利用 `adb_helper` 打指令或 `ui` 點畫面，最後呼叫 `reporter.add_result(Category, Name, True/False, Message)` 記錄成績。
4.  在 `main.py` 中 `import` 該模組，並加進執行序列中即可！無須更動任何核心層代碼。
