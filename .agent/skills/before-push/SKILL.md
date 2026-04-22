# Skill: Before-Push Industrialization Workflow

## Description
本技能用於在執行 `git commit` 與 `git push` 前，執行一系列標準化結案動作。包含文檔同步、安全編輯規範、暫存狀態檢查與使用者核決。
當使用者提到「準備 commit」、「要 push 了」、「結案流程」、「執行 before-push」或「準備提交」時，應觸發此技能。

## Instructions

每當觸發此流程時，請嚴格執行以下四個階段：

### Phase 1: 變更分析與文檔草擬 (Preparation)
1. **變更分析**：執行 `git diff` 總結本次代碼變動核心。
2. **文檔更新細則 (Drafting Rules)**：
   - **CHANGELOG.md (鋼鐵防禦)**：讀取內容，嚴禁覆寫歷史，使用 `prepend` 策略新增今日紀錄。
   - **TODO.md (進度核對)**：更新最後維護日期。檢查本次變更是否對應某個項目，完成則標記為 `[x]` 並記錄日期。
   - **README.md (手冊同步)**：若新增 CLI 參數或變更路徑，必須同步更新 README，且**必須針對新參數撰寫完整的「使用情境」與「指令範例」**。
   - **PRD.md (架構同步)**：若涉及核心架構或產品定義，必須同步更新 PRD.md。
3. **技術約束 (Safety Constraints)**：
   - **禁止全量覆寫**：針對超過 100 行的檔案，必須使用 `multi_replace_file_content`。
   - **特殊字元防護**：若文檔包含 Emoji 或嵌套代碼塊，必須先精確定位行號，嚴禁盲目匹配。

### Phase 2: 暫存與狀態展示 (Staging)
1. **執行暫存**：執行 `git add .` (或特定檔案)。
2. **獲取狀態**：執行 `git status`。

### Phase 3: 使用者最終核決 (Human Review) - [強制停止點]
1. **展示現狀**：向使用者完整展示 `git status` 結果。
2. **清查產物**：主動列出 **Untracked files**，提醒使用者是否有暫態 debug 檔案需要移除。
3. **請求核准**：停止所有自動操作。報告：「變更已暫存，請確認內容與清單。確認無誤後，請指示我執行 Final Commit。」

### Phase 4: 最終執行 (Execution)
1. **核准後提交**：僅在獲得明確指示後，撰寫高描述性的 Commit Message。
2. **推送**：執行 `git commit` 與 `git push`。
