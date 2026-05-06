---
name: before-push
description: 此 Skill 用於在執行 `git commit` 或 `git push` 之前，確保所有必要的文檔（CHANGELOG, README, TODO）已根據代碼變更進行同步更新
---

# Before Push Skill

此 Skill 用於在執行 `git commit` 或 `git push` 之前，確保所有必要的文檔（CHANGELOG, README, TODO）已根據代碼變更進行同步更新。

## [Documentation Protection Protocol]

### 1. CHANGELOG.md 規範
- **禁止全量覆寫**。
- **必須採用 Prepend (加在最前面) 策略**。
- 修改前必須先讀取當前內容，並確保歷史紀錄 (日期、版本) 完全保留。
- 新增內容應包含：版本號、日期、Added、Changed、Fixed 區塊。

### 2. README.md 規範
- 修改特定區塊時，**優先使用 multi_replace_file_content** 進行精確替換。
- 避免破壞其他不相關的章節（如技術文檔連結、環境準備說明）。

### 3. TODO.md 規範
- 每當完成一項開發任務，必須主動更新此檔案的狀態。
- 將 `[ ]` 更新為 `[x]` 並標註完成日期。

## [Execution Steps]

1. **分析變更**：讀取當前暫存的代碼變更內容。
2. **更新文檔**：按照上述規範更新 CHANGELOG, README 和 TODO。
3. **驗證狀態**：執行 `git status` 確認所有變更已加入暫存。
4. **提交代碼**：產出具備描述性的 Commit Message 並執行提交。
