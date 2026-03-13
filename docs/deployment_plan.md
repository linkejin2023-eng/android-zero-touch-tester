# Deployment Test Plan & Clean Environment Simulation / 部署測試計畫與純淨環境模擬

To ensure the tool works seamlessly on other computers (especially corporate domain machines), we will simulate a "Clean Room" setup.
為了確保工具在其他電腦（特別是公司網域電腦）上能順利運作，我們將模擬「無塵室」建立流程。

## 1. Clean Environment Strategy / 純淨環境策略

We will use a **Docker-based approach** (if available) or a **Native Clean Python Environment** to verify the README steps.
我們將使用 **Docker**（如果可用）或 **原生純淨 Python 環境** 來驗證 README 步驟。

### A. Docker (Recommended for true OS isolation) / Docker (推薦：真實 OS 隔離)
- **Goal / 目標**: Simulate a fresh Linux install / 模擬全新的 Linux 安裝。
- **Why / 原因**: Ensures no hidden system dependencies exist / 確保不存在隱藏的系統依賴。
- **Method / 方法**: Use a basic `ubuntu:22.04` image / 使用基礎 `ubuntu:22.04` 鏡像。

### B. Native Virtualenv (Python isolation) / 原生虛擬環境 (Python 隔離)
- **Goal / 目標**: Verify `requirements.txt` / 驗證依賴清單。
- **Method / 方法**: Create a fresh `venv` in a temporary directory / 在臨時目錄建立全新的 `venv`。

## 2. Key Deployment Hazards / 部署關鍵風險

| Hazard / 風險 | Impact / 影響 | Verification Step / 驗證步驟 |
| :--- | :--- | :--- |
| **USB Permissions** / USB 權限 | `pyusb` will fail (Access Denied) | Test `setup_permissions.sh` & udev rules. |
| **Missing ADB/Fastboot** / 缺少二進位檔 | Flash and Test logic will fail | Check if `PATH` is updated. |
| **Python Dependencies** / Python 依賴 | `ModuleNotFoundError` | Verify `pip install -r requirements.txt`. |
| **Sudo Requirements** / Sudo 需求 | Company security blocks `sudo` | Ensure no-sudo run after initial udev setup. |

## 3. Deployment Simulation Workflow / 部署模擬工作流

1. **Package / 打包**: Zip the current project (excluding `__pycache__`).
2. **Setup / 安裝**: Move to `/tmp/CleanTest`.
3. **Execute / 執行**: Follow [README.md](file:///home/franck/桌面/Sanity_Test/README.md) step-by-step.
4. **Fix / 修正**: Update `setup_permissions.sh` or `README.md` if any step fails.

## 4. Next Step Actions / 後續行動

- [x] Create `requirements.txt` (Generated! ✅)
- [ ] Create a `deployment_verify.py` diagnostic script / 建立環境診斷腳本。

## 5. Zero-Install Python Strategy / 零安裝 Python 策略 (Avoid System Pollution)

If the corporate machine only has Python 3.6, you can bring your own **Portable Python** without installing anything globally or requiring `sudo`.
如果公司電腦只有 3.6，你可以直接攜帶 **便攜式 Python (Portable Python)**，不需安裝、不需 `sudo`。

1. **Download Standalone Python**: Get a pre-compiled Linux binary (e.g., from [indygreg/python-build-standalone](https://github.com/indygreg/python-build-standalone/releases)).
2. **Unzip**: Place it in a folder (e.g., `~/python310`).
3. **Use for venv**: Creating the virtual environment using the *portable* binary path:
   ```bash
   ~/python310/bin/python3 -m venv .venv
   source .venv/bin/activate
   # Now (.venv) python --version will be 3.10+
   ```
   *Benefit*: Complete physical isolation. No root required. Zero system change.
   *優點*：物理隔離。無需 root，對系統零動動。

## 6. Professional Version Managers / 專業版本管理工具

If you want a more permanent way to switch versions on your dev machine:
如果你想要在開發機上更優雅地切換版本：

### A. pyenv (Developer's Choice)
- **What it is**: A tool specifically for switching between multiple Python versions.
- **How it works**: It installs Python versions into `~/.pyenv/versions/`. You can switch globally or per-folder.
- **Safety**: High. It doesn't overwrite `/usr/bin/python`.
- **Command**: `pyenv install 3.10.0` -> `pyenv local 3.10.0`.
- **說明**：專為切換 Python 版本設計的工具。安裝在 `~/.pyenv`，不影響系統全域路徑。

### B. Conda / Miniconda (Enterprise Standard)
- **What it is**: A powerful environment manager that bundles its own Python.
- **How it works**: It is completely self-contained in its own directory.
- **Safety**: Very High. Recommended for corporate machines with strict separation requirements.
- **Command**: `conda create -n mytest python=3.10` -> `conda activate mytest`.
- **說明**：企業級環境管理器。自帶 Python 與依賴管理，隔離性極強，適合網域電腦。
