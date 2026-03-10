# 更新日誌 (Changelog)

所有關於本專案的顯著變更將會記錄於此檔案中。

## [2026-03-09] - 技術探索與文檔重構
### Added (新增)
- 建立專案管理所需之 `README.md` (包含進度儀表板)、`CHANGELOG.md` 及 `docs/` 技術文檔目錄。
- 確立 Phase 3 開發目標 (藍牙設備掃描、相機 JPG 存檔驗證、手電筒硬體控制)。
- 擴增 Phase 4 (WWAN 無卡/有卡雙情境檢測、麥克風錄音、影片硬解、重啟穩定性) 與 Phase 5 (SMTP Email 寄發與 Logcat 打包整合) 藍圖。
- 完成 Setup Wizard 突破性研究，確立 AOAv2 HID 免 Root / 免特製硬體的合法軟體後門解法。

### Changed (變更)
- 依據終端測試設備與網路限制，自未來規劃中**剔除**：SD 卡掛載測試 (無卡槽)、震動馬達測試 (無硬體元件)、通訊軟體網路推播 (權限網域阻擋)。改以單純 Email 發送報告。

## [2026-03-06] - Phase 2 完結與全自動化達標
### Added (新增)
- 導入 Phase 2 進階測試模組：`test_touch.py`, `test_sensors_advanced.py`, `test_housekeeper.py`, `test_buttons.py`, `test_nfc.py`, `test_gps.py`。
- 實現 29 項 Android Sanity 測試全自動化 (耗時約 82 秒)。

### Fixed (修復)
- 解決 `test_camera.py` 因 `settings.intelligence` (選擇相機 App) 彈出窗導致的 UIAutomator 卡死問題。改為被動認可 Intent Resolver 的存在即為 Pass。
- 修復 `test_connectivity.py` 中 WiFi 連線後 DHCP 取號超時 (Timeout) 導致誤判 Failed 的問題，將等候時間延長至 15 秒。
- 將 LED 測試從讀取 `/sys/class/leds/` (User Build 權限阻擋) 更改為解析 `dumpsys lights` 服務狀態。
