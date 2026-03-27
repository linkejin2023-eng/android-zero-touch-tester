# Changelog

所有關於本專案的顯著變更將會記錄於此檔案中。

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
