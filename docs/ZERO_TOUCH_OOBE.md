# 突破性的 OOBE (Setup Wizard) 自動化策略 🌟

本篇文檔記錄了在 Android User Build 上實現「免修改系統、免特定硬體、免觸控」的 100% 全自動化突破思路。

## 1. 自動化最大的死敵：開機精靈 (Setup Wizard / OOBE)
在刷入最新的 Android OS（且為無法解鎖 Bootloader 的 User Build）後，系統開機將無可避免地進入「開機精靈」(OOBE)。
此時 Android 為防禦駭客與保護隱私，**USB Debugging (ADB) 預設是全數關閉的**。

**死局**：自動化腳本靠 ADB 去推動，但我們沒有 ADB；要打開 ADB 必須去點螢幕並通過開機精靈，那就變成「非自動化」了。

## 2. 我們走過但被捨棄的「歪路」

### ❌ 竄改 OS 的 `build.prop`
*   **做法**：把 `ro.setupwizard.mode=DISABLED` 寫入系統。
*   **死因**：這需要 Unlocked Bootloader 刷 custom recovery (如 TWRP) 才能有權限改寫 `/system`，違反了我們驗證原廠 User Build 的宗旨。

### ❌ Android MDM QR Code 企業註冊
*   **做法**：在開機畫面點 6 下開啟相機，掃描寫有特殊 payload 的 QR Code。
*   **死因**：首先「點 6 下加對準鏡頭掃描」還是人工的；其次，AOSP 標準的企業 Payload 給你下裝 DPC App 與配網的功能，但**並沒有參數能讓你一掃就自動打開 `adb_enabled = 1`**。

### ❌ Linux USB Gadget API (被主機硬體打臉)
*   **做法**：目前最標準的想法是利用 Linux 電腦中的 `/sys/class/udc`，依靠 `libcomposite` 把開發/測試用電腦的 USB Type-C 接口 **「虛擬化成標準 USB 鍵盤」**，把 Android 騙倒，然後送出鍵盤敲擊盲解。
*   **死因**：絕大多數的一般筆電（包含本開發案使用的 Dell XPS 的 Intel 晶片組），其 USB Controller **只限於做 Host (主機)，根本不支援 Dual-Role (UDC) 裝置模式切換**。也就是說，物理硬體能力決定了這台電腦「裝不出鍵盤的樣子」。

---

## 3. 終極突破：發現 AOAv2 HID 這條軟體後門

拋棄常規的 USB Class 思維後，我們向 Google 在 Android 源碼 (AOSP) 埋下的專用通訊協定尋找。並挖出了極冷門但能力外掛級的解法 —— **AOAv2 (Android Open Accessory Protocol 2.0)**。

### 這是什麼神仙技術？
AOAv2 最初是設計給車機、特殊音響配件來**控制手機**用的。它具備 `AOAv2 HID Support` 的超狂逆轉機甲：
它可以讓 **筆電保持高高在上的 Host (主機) 身分不變**，強制令連接的 Android 手機切換成 "Accessory Mode" 面對你。在進入這模式後，Android 系統大腦會「敞開大門，把 Host 塞進來的特製 Control Requests，強制生吞活剝地視為底層硬體鍵盤/滑鼠的 Input Event 打字訊號」！

### 為什麼這能完美解決 OOBE 盲打？
1.  **無視 ADB 封鎖**：這是在 USB 最最底層的原生 AOSP 協定，即便是在 Setup Wizard 剛開機黑屏，插路線就能生效。
2.  **不挑電腦硬體**：你的筆電不用換昂貴的 Linux 主機板、不用支援 UDC，因為筆電還是 Host，靠著 Python `pyusb` 這個 User-space 函式庫就能強發 Control transfer (控制傳輸)。
3.  **合法且強大**：不需硬改系統，這是原本就存在於每一台 Android 的功能。

### 零觸控實現步驟 (POC 雛型原理)
只要寫一隻 `aoa_keyboard.py` 放到這台普通的沒特異功能的筆電上：
1.  電腦發起 USB `vendor spec` 控制封包找尋 Android。
2.  啟動 AOA Handshake，讓手機的 USB VID/PID 切成 `0x2D00` 系列（進入配件模式）。
3.  向 Android 的 Endpoint 0 (EP0) 寫入 `ACCESSORY_REGISTER_HID` 控制請求，註冊一個假鍵盤 ID 與對應的 HID Descriptor 表格。
4.  對著被控制的 Android 發狂丟出 `ACCESSORY_SEND_HID_EVENT`：`Tab`, `Enter`, `↑`, `↓`...
5.  **盲打成功結案**：你的 Python 就在這台 User Build 原廠機精靈畫面中，利用虛擬按鍵把 OOBE 解完，順便進開發者選項打開 `USB Debugging` 交棒回 ADB 身上。

### 結論
除了買一個 BadUSB 或 Raspberry Pi Pico 插上去之外，**發現並透過 AOAv2 HID 來作為 OOBE 解鎖者，是目前純軟體能達到 100% OOBE 解鎖最高境界的唯一方案。**
