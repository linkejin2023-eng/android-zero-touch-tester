# Android Sanity Test Automation 

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
| **Phase 5: 企業級派發與 CI/CD** | 暫停 | **60%** | Email 總結報告發送、失敗日誌 (Logcat) ZIP 打包 | 2026-03-13 |
| **Feature: 自動化燒錄 (Flash) 模組** | 完結 | **100%** | 支援 ZIP 自動解壓、Fastboot 流程與燒錄後自動接續 OOBE | 2026-03-12 |
| **Feature: 多 SKU (GMS/China) 支援** | 完結 | **100%** | 實作自適應 Branching 序列，支援 SIM/No-SIM 雙場景自動 OOBE Bypass | 2026-03-25 |
| **Phase 6: 跨電腦部署與相容性** | 完結 | **100%** | 實作 Portable Python 3.11 部署方案、本地指令自動偵測與 venv 隔離 | 2026-03-18 |
| **[T70] Phase 1: 核心架構與守門員規則** | 完結 | **100%** | Security Check、Config 控制、Baseline 核驗 | 2026-03-27 |
| **[T70] Phase 2: 演算法與穩定度優化** | 完結 | **100%** | Sensor 熵值分析、GPS 弱訊號、視力報表翻新 | 2026-03-27 |
| **[T70] Phase 2.1: 硬體強韌化** | 完結 | **100%** | 三段式硬體快門、自動解鎖 (Lock Screen Bypass) | 2026-03-27 |
| **[T70] Phase 3: 資料生命週期與收尾** | 進行中 | **20%** | SKU Mapping、Legacy 清除、UserData 擦除 | 2026-03-27 |
| **[T70] Phase 4: 資料驅動全自動驗證 (Data-Driven)** | 完結 | **100%** | JSON 屬性自適應、混合提取引擎 (shell/logcat/ui)、免寫 Code 新增韌體測項 | 2026-04-01 |

---

## 專案亮點 (Highlights)
1. **100% 免接觸 (Zero-Touch) 軟體解鎖**：領先業界實作鎖定畫面自動偵測與盲打解鎖，確保測試不因裝置休眠而中斷。
2. **音訊/感測器「生存」驗證**：透過方差與熵值 (Entropy) 數學模型，在靜止狀態下精確判定麥克風與加速度計硬體存活。
3. **三段式相機快門策略**：優先發動硬體鍵值 (Keyevent 27)，具備跨 App 版本的極高維護性與相容性。
4. **自動化 HTML 報告與發布建議**：一鍵產生清楚的綠/紅 Pass 表單，並基於成敗給出 `Release Recommendation`。

## 目錄與技術文檔 (Documentation)
所有的設計細節、技術突破與測試覆蓋範圍，皆詳載於 `docs/` 資料夾下：

* [**測試框架設計 (ARCHITECTURE.md)**](docs/ARCHITECTURE.md) - 解釋結合 ADB System Level 與 UIAutomator 的混合層次驗證策略。
* [**自動化涵蓋範圍與策略 (TEST_COVERAGE.md)**](docs/TEST_COVERAGE.md) - 詳細列出 29 項測試的方法轉換，如何把物理動作變為軟體指令。
* [**終極突破：零觸控 OOBE (ZERO_TOUCH_OOBE.md)**](docs/ZERO_TOUCH_OOBE.md) - 深入探討為何選擇 AOAv2 協定作為 Setup Wizard 封鎖下的唯一純軟體解答。

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

### ️ CLI 參數說明
```bash
# 情境 A:- **僅執行測試 (裝置已在 Home Screen)**:
 ```bash
 python3 main.py --only-tests
 ```
- **完整流程 (Flash + OOBE + Tests)**:
python3 main.py --flash /path/to/fastboot.zip

# 情境 B: China SKU 全自動 (燒錄 + 中國版 OOBE + 執行測試)
python3 main.py --flash /path/to/fastboot.zip --sku china

# 情境 C: 僅繞過 OOBE (不燒錄，僅執行 AOA 盲打與 ADB 授權)
python3 main.py --oobe --sku china --skip-tests

# 情境 D: 標準測試 (裝置已在 Home Screen 且開啟 ADB)
python3 main.py
```

### 4. 參數說明
- `--flash <path>`: 指定燒錄包路徑，支援自動解壓縮。
- `--oobe`: 啟動 AOA HID 盲打流程，自動解除 OOBE 並開啟 ADB。
- `--sku <gms|china>`: 指定產品 SKU（預設為 `gms`）。會切換不同的 OOBE 盲打序列與 ADB 授權路徑。
- `--skip-tests`: 僅執行燒錄與 OOBE 解除，完成後立即退出，不執行功能測試。

### 5. 查看報告
執行完畢後，HTML 測試報告將自動產生於 `reports/` 目錄中。
