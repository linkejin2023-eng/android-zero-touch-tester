# Android Zero-Touch CI/CD Engine (Jenkins-style)

將原本的 Polling 監控改造成更專業、由 Build Server 主動觸發 (Push-based) 的自動化引擎，模仿 Jenkins 的「任務-工作空間」管理模式。

## User Review Required

> [!IMPORTANT]
> **觸發方式 (Trigger)**：Build Server 需在完成上傳後，發送 HTTP POST 請求給測試機。
> 格式範例：`curl -X POST -d '{"build_number": "REL_02.01.04.N.260212", "type": "user"}' http://test-server:8080/trigger`

> [!IMPORTANT]
> **零依賴實作**：為確保測試機環境純淨，我們將使用 Python 內建的 `http.server` 實作監聽器，無需安裝 Flask 或 FastAPI。

## Proposed Changes

### 1. 監聽與調度引擎 (Engine & Listener)

- **[NEW] \`monitor/engine.py\`**：核心服務。
  - **HTTP Server**：監聽指定 Port (預設 8080)，接收 Build Server 通知。
  - **Task Queue**：內部使用 \`queue.Queue\` 確保任務排隊執行，避免搶奪 ADB 資源。
  - **Worker Thread**：背景執行緒，從佇列拿取任務並進行測試。

### 2. 工作空間管理 (Workspace Management)

- **核心設計**：每個測試任務都有專屬目錄 \`workspaces/{build_number}_{type}/\`。
- **隔離隔離 (Isolation)**：
  - 燒錄檔、Console Log、HTML 報告全部儲存在該目錄下。
  - **[MODIFY] \`monitor/database.py\`**：新增 \`workspace_path\` 欄位，讓資料庫與實體檔案對齊。

### 3. 多 SKU 自動判定 (Automated Logic)

- **[NEW] \`monitor/logic.py\`**：抽離命名規則判定邏輯。
  - 偵測 \`.N.\` 自動給予 \`--sku china\` 參數。
  - 未來若有更多規則，集中在此處維護。

### 4. 智慧清理機制 (Smart Cleanup)

- **策略**：**刪除 Image，保留 Log**。
- 測試結束後，執行清理：
  - 保留最新 2 份 Workspace 內的 \`fastboot.zip\`。
  - 對於更舊的 Workspace，僅刪除 \`*.zip\`，保留 \`*.log\` 與 \`*.html\`。

---

## 工作流程圖 (Jenkins-like Pipeline)

\`\`\`mermaid
sequenceDiagram
    participant BS as Build Server
    participant Eng as Engine (Listener)
    participant Worker as Worker Thread
    participant WS as Workspace Folder
    
    BS->>Eng: HTTP POST /trigger (Build Info)
    Eng-->>BS: 200 OK (Job Queued)
    Eng->>Worker: Dispatch Job
    Worker->>WS: 1. Create Workspace
    Worker->>WS: 2. Fetch/Copy Image
    Worker->>WS: 3. Run Flash & Test (Pipe to console.log)
    Worker->>WS: 4. Generate & Save HTML Report
    Worker->>Worker: 5. Cleanup Old Zips
    Worker-->>Worker: 6. Update SQLite History
\`\`\`

---

## Open Questions

1. **Port 設定**：8080 是否可以使用？還是需要避開公司常用埠號？
2. **對外通知**：雖然 Jenkins 會有 Web UI，但目前是否先以「Console Log」與「HTML Report」為主，等待下一步的 Web Server 開發？

## Verification Plan

### Automated Tests
1. 使用 \`scripts/trigger_mock_build.py\` 發送 POST 請求模擬觸發。
2. 驗證 \`workspaces/\` 目錄是否正確建立並包含對應檔案。
3. 驗證 \`console.log\` 是否即時補捉到 \`main.py\` 的輸出。

### Manual Verification
1. 連續發送 3 個不同版本的請求，驗證佇列排隊機制。
2. 檢查最舊版本的 Workspace，確認 \`fastboot.zip\` 已被刪除而 \`.log\` 還在。
