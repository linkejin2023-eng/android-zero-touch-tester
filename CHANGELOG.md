# Changelog

所有關於本專案的顯著變更將會記錄於此檔案中。

## [2026-03-18] - 企業部署成功與指令偵測優化
### Fixed (修正)
- **ADB/Fastboot 偵測邏輯優化**：修復了當系統未安裝 adb/fastboot 分別時，誤將「command not found」報錯訊息識別為 Android 裝置的 Bug。
- **偵測精準度提升**：改用嚴格的序號 (Serial) 正則匹配，確保連線狀態判斷 100% 正確。

### Changed (變更)
- **Portable Python 部署方案正式驗證**：確認在 Python 3.6 的舊版企業環境中，透過 Standalone Python 3.11 引擎可完全打通自動化測試流程。
- **本地指令優先機制**：`FlashManager` 現在會自動偵測並優先使用燒錄包內建的 `fastboot` 二進制檔，大幅降低環境依賴。

## [2026-03-13] - 架構優化、多 SKU 支援與跨電腦部署規劃
### Added (新增)
- **多 SKU 支援正式實作**：
    - 引進 `--sku <gms|china>` 參數，動態切換 AOA HID 盲打序列。
    - 實作 China SKU (NAL) 專用 OOBE 跳過邏輯與 ADB 授權路徑調校。
- **跨電腦部署規劃 (進行中)**：
    - 生成 `requirements.txt` 與環境診斷工具 `check_env.py`。
    - 撰寫 `deployment_plan.md` 與安全性評估報告。
    - **Legacy Compatibility**：規劃將核心代碼回溯至 Python 3.6+ 相容語法以適應公司電腦。

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
