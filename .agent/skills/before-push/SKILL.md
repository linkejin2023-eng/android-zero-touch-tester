# Skill: Before-Push Industrialization Workflow

## Description
本技能用於在執行 `git commit` 與 `git push` 前，確保所有專案文檔（CHANGELOG, README, TODO）已根據當次代碼變更完成同步更新，並嚴格保護歷史紀錄不被覆寫。

## Instructions

每當使用者要求「執行提交流程」或「準備 push」時，請嚴格執行以下步驟：

### Step 1: 變更分析 (Change Analysis)
1. 執行 `git status` 與 `git diff` 了解本次代碼變動的核心。
2. 總結變動內容（例如：修正了哪個 Bug、新增了哪個參數）。

### Step 2: 歷史保護與精確更新 (Safe Documentation Update)
1. **CHANGELOG.md (鋼鐵防禦)**：
   - **必須**先讀取目前檔案。
   - **禁止**覆寫舊有日期與歷史紀錄。
   - **必須**使用 `prepend` 策略，將新版本與今日日期加在最上方。
2. **TODO.md (進度核對)**：
   - 檢查本次變更是否對應到 `TODO.md` 中的某個項目。
   - 若已完成，將其標記為 `[x]` 並加上完成日期。
3. **README.md & PRD.md (手冊與架構同步)**：
   - 若新增了 CLI 參數或變更了路徑，必須同步更新 README.md。
   - 若涉及核心架構或產品定義變更，必須同步更新 PRD.md。
4. **技術約束 (Safety Constraints)**：
   - **禁止全量覆寫**：針對超過 100 行的文檔，必須使用 `multi_replace_file_content` 進行局部替換。
   - **特殊字元防護**：若文檔包含 Emoji 或嵌套代碼塊，必須先精確定位行號，嚴禁盲目匹配。

### Step 3: 品質與同步檢查 (Sanity Check)
1. 確保 `config.yaml` 的預設值符合生產環境需求。
2. 確保沒有遺漏任何 untracked 的新檔案。

### Step 4: 最終提交 (Final Commit)
1. 撰寫具備高度描述性的 Commit Message（包含變更類型與影響範圍）。
2. 執行 `git add`, `git commit` 與 `git push`。

## Usage
當使用者說出以下關鍵字時觸發：
- "準備 commit"
- "執行 before-push 流程"
- "幫我結案並推送到 git"
