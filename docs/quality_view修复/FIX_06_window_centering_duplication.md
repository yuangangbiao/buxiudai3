# FIX-06: 窗口居中代码重复消除

## 1. 问题定位

| 项目 | 内容 |
|------|------|
| **文件** | `views/quality_view.py` |
| **出现位置** | **位置 A**: `add_record()` → `on_save()` 第 556-560 行 |
| | **位置 B**: `_show_completion_confirm()` 第 581-585 行 |
| **代码量** | 每处 ~5 行，共 ~10 行 |
| **严重度** | 🟢 低 |

## 2. 问题描述

两处代码执行了**完全相同的窗口居中定位模式**：

### 位置 A（L556-560）：
```python
info_win.attributes("-topmost", True)
info_win.update_idletasks()
x = (info_win.winfo_screenwidth() // 2) - 200
y = (info_win.winfo_screenheight() // 2) - 170
info_win.geometry(f"400x340+{x}+{y}")
```

### 位置 B（L581-585）：
```python
win.attributes("-topmost", True)
win.update_idletasks()
x = (win.winfo_screenwidth() // 2) - 230
y = (win.winfo_screenheight() // 2) - 190
win.geometry(f"460x380+{x}+{y}")
```

**差异仅在窗口尺寸**（400x340 vs 460x380），模式完全一致。

**根本问题**：
1. DRY 原则违反：手动计算居中位置的代码重复出现
2. `utils/window_manager.py` 中已提供 `setup_resizable_window()` 函数，但未在对话框创建中使用
3. 如果今后类似的对话框增加，居中代码会继续扩散

## 3. 修复目标

使用 `utils/window_manager.py` 中的 `setup_resizable_window()` 统一处理窗口定位，或提取公共居中函数到 `dialogs/base.py`。

## 4. 具体实现步骤

### Step 1: 分析 `setup_resizable_window()` 的兼容性

`utils/window_manager.py` 的 `setup_resizable_window(window, window_key, default_geometry)`：
- 功能：设置窗口大小、居中定位、保存/恢复窗口位置
- 需要 `window_key` 字符串参数
- 默认自动居中

确认后选择方案。

### Step 2: 实施修复

#### 方案 A（推荐）：在 `dialogs/base.py` 新增 `center_window()` 辅助函数

```python
def center_window(window, width, height, topmost=False):
    """将窗口居中显示在屏幕中央"""
    if topmost:
        window.attributes("-topmost", True)
    window.update_idletasks()
    x = (window.winfo_screenwidth() // 2) - (width // 2)
    y = (window.winfo_screenheight() // 2) - (height // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")
```

然后在 `quality_view.py` 中替换：
```python
# 位置 A（L556-560）→
center_window(info_win, 400, 340, topmost=True)

# 位置 B（L581-585）→ 但 B 在 FIX-03 中将被整体提取，实际只需处理 A
```

#### 方案 B：使用已有的 `setup_resizable_window()`

```python
# 位置 A：
from utils.window_manager import setup_resizable_window
setup_resizable_window(info_win, "save_success", "400x340")

# 位置 B：将被 FIX-03 处理
```

### 方案对比

| 方案 | 优点 | 缺点 | 推荐 |
|------|------|------|:----:|
| **A: 新增 `center_window()`** | 简单清晰，零依赖，低侵入 | 增加一个辅助函数 | ⭐（如仅2处） |
| **B: 使用 `setup_resizable_window()`** | 复用已有函数，功能更全 | 需要传入 `window_key`，复杂度高 | （如更多场景） |

## 5. 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `views/dialogs/base.py` | ✅ 新增 | 新增 `center_window()` 辅助函数 |
| `views/quality_view.py` | ✅ 修改 | 位置 A 替换为 `center_window()` |
| `views/dialogs/__init__.py` | ✅ 修改 | 导出 `center_window`（如采用方案 A） |

## 6. 依赖关系

| 前置依赖 | 说明 |
|----------|------|
| 无 | 可独立进行 |

## 7. 风险与注意事项

- **位置 A**：`add_record()` 中的 `info_win` 设置 `-topmost`，需在 `center_window()` 中保留此参数
- **位置 B**：`_show_completion_confirm()` 将在 FIX-03 中被提取为独立 Dialog 类，其居中逻辑由 `setup_resizable_window()` 统一处理，**不需要单独修复**
- **`alert()` 居中**：`alert()` 函数本身也有居中定位（`dialogs/base.py` L21-23），但它的居中更简单，可以不处理

## 8. 验收标准

| # | 标准 | 验证方式 |
|---|------|---------|
| 1 | 保存成功窗口位置居中 | 视觉确认 |
| 2 | 窗口尺寸（400x340）不变 | 视觉确认 |
| 3 | 窗口置顶属性保留 | 观察 |

## 9. 预估工作量

- 新增 base.py：~10 行
- 修改 quality_view.py：删除 ~5 行，新增 ~1 行
- 修改 __init__.py：新增 ~1 行
- **净减少代码量：~4 行**
