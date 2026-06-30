# Python 运行环境规范

> **版本**: v1.0
> **更新日期**: 2026-06-15
> **适用范围**: 所有 Python 脚本和命令执行

---

## 🔧 正确的 Python 运行环境

### Windows 系统

#### 主运行环境（推荐）

| 属性 | 值 |
|------|-----|
| **路径** | `C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\python.exe` |
| **版本** | Python 3.14.3 |
| **用途** | 项目主运行环境 |

#### 备选运行环境

| 属性 | 值 |
|------|-----|
| **路径** | `C:\Users\lenovo\AppData\Local\Programs\Python\Python313\python.exe` |
| **版本** | Python 3.13.0 |
| **用途** | 备选运行环境 |

---

## 🚀 常用命令

### 运行 Python 脚本

```powershell
& "C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\python.exe" script.py
```

### 运行测试

```powershell
& "C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m pytest
```

### 安装依赖

```powershell
& "C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\Scripts\pip.exe" install flask
```

---

## 📋 项目 Python 版本要求

根据 `requirements.txt` 和 `pyproject.toml`:

| 依赖 | 版本要求 |
|------|---------|
| flask | >=3.1.0 |
| werkzeug | >=3.1.0 |
| pymysql | >=1.2.0 |
| PyJWT | >=2.13.0 |

**最低 Python 版本**: 3.10+

---

## ⚠️ 注意事项

1. **不要使用 PATH 中的默认 `python` 命令**
   - PATH 中的 python 可能指向错误的版本
   - 会导致 `ModuleNotFoundError` 错误

2. **始终使用完整路径**
   ```powershell
   # ❌ 错误
   python script.py

   # ✅ 正确
   & "C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\python.exe" script.py
   ```

3. **本项目的 AI 助手（TRAE）**
   - 使用独立的 Python 环境
   - 路径: `C:\Users\lenovo\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\vm\tools\python`
   - 版本: Python 3.10.11
   - **不适用于运行项目代码**（缺少依赖）

---

## 🔍 验证环境

```powershell
# 检查 Python 版本
& "C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\python.exe" --version
# 输出: Python 3.14.3

# 检查 flask 是否可用
& "C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\python.exe" -c "import flask; print(flask.__version__)"
# 输出: 3.1.3

# 检查项目模块是否可导入
& "C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\python.exe" -c "
import sys
sys.path.insert(0, 'd:/yuan/不锈钢网带跟单3.0/mobile_api_ai')
from storage.mysql_storage import MySQLStorage
print('MySQLStorage OK')
"
```

---

## 📝 常见问题

### Q: 为什么 `python --version` 显示的不是 3.14.3？

A: PATH 环境变量中可能有其他 Python 版本。请使用完整路径。

### Q: 如何永久设置默认 Python？

A: 不建议修改系统 PATH，可能影响其他应用。推荐使用完整路径。

### Q: 如何在项目中设置 Python 路径？

A: 在 `.vscode/settings.json` 或 `.env` 文件中设置 `PYTHON_PATH`。

---

**强制执行日期**: 2026-06-15
