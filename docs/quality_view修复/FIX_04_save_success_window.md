# FIX-04: `add_record()` 中内联 Toplevel 保存成功窗口替换

## 1. 问题定位

| 项目 | 内容 |
|------|------|
| **文件** | `views/quality_view.py` |
| **方法** | `QualityView.add_record()` → `on_save()` 回调内部 |
| **行号** | 第 552 行 — 第 568 行（共 17 行） |
| **代码量** | ~17 行 |
| **严重度** | 🟢 低 |

## 2. 问题描述

在 `add_record()` 方法的 `on_save()` 回调中，最后一部分（L552-568）创建了一个保存成功的信息展示窗口：

```python
info_win = tk.Toplevel(self)          # L552
info_win.title("保存成功")             # L553
info_win.geometry("400x340")           # L554
info_win.resizable(False, False)       # L555
info_win.attributes("-topmost", True)  # L556
info_win.update_idletasks()            # L557
x = (info_win.winfo_screenwidth() // 2) - 200   # L558
y = (info_win.winfo_screenheight() // 2) - 170  # L559
info_win.geometry(f"400x340+{x}+{y}") # L560
# ... Label + Frame + Button + 快捷键绑定 (L562-568)
```

**根本问题**：
1. `dialogs/base.py` 中已有 `alert()` 函数可完全替代此功能
2. 内联创建 Toplevel 增加视图代码膨胀
3. 与 FIX-06 的居中代码模式重复
4. 信息窗口中展示的 `record_info` 仅为格式化文本，完全适合 `alert()` 调用

## 3. 修复目标

将 L552-568 的内联 Toplevel 保存成功窗口替换为 `alert(record_info, "保存成功")` 调用。同时将 `record_info` 的构建逻辑保留在原地或提取为辅助函数。

## 4. 具体实现步骤

### Step 1: 分析 `alert()` 的兼容性

现有 `alert()` 函数（`dialogs/base.py` L14-27）：
```python
def alert(message, title="提示"):
    win = tk.Toplevel()
    win.title(title)
    win.geometry("350x120+...")
    tk.Label(win, text=message, font=FONTS["body"], wraplength=320)
    ttk.Button(win, text="确定", command=win.destroy)
```

需要确认：
- `alert()` 的窗口尺寸（350x120）是否能容纳 `record_info` 的多行文本 → 可能需要增大或支持自动调整
- `wraplength=320` 是否足够 → 当前 `record_info` 每行约 40 个中文字符，320px 可能不足

### Step 2: 增强 `alert()`（如需）

如 `alert()` 尺寸不足，先增强 `alert()` 支持 `width` 和 `height` 参数：

```python
def alert(message, title="提示", width=350, height=None):
    if height is None:
        # 根据消息行数自动计算高度
        lines = message.count('\n') + 1
        height = max(120, min(lines * 22 + 80, 500))
    win.geometry(f"{width}x{height}+...")
```

### Step 3: 替换保存成功窗口

将 L552-568 的代码替换为：

```python
alert(record_info, "保存成功")
```

### 备选方案（如果 `alert()` 增强也不合适）

如果 `alert()` 无法满足展示需求，创建极简的 `show_info()` 函数：

```python
def show_info(message, title="信息", width=400, height=340):
    """展示多行信息弹窗"""
    # 封装了 Toplevel + Label + Button + 居中的样板代码
```

## 5. 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `views/quality_view.py` | ✅ 修改 | L552-568 替换为 `alert()` 调用 |
| `views/dialogs/base.py` | ✅ 可能增强 | `alert()` 增加 width/height 参数支持 |

## 6. 依赖关系

| 前置依赖 | 说明 |
|----------|------|
| 无 | 可独立进行（建议在 FIX-06 之后） |

## 7. 风险与注意事项

- **信息展示完整性**：`record_info` 包含格式化文本，`alert()` 的 `wraplength` 需足够宽
- **窗口置顶**：原窗口设置 `-topmost`，需在 `alert()` 中保留
- **快捷键绑定**：原窗口绑定了 Enter/Escape 关闭，`alert()` 已有"确定"按钮
- **最小改动原则**：仅替换 L552-568 的窗口创建部分，`record_info` 文本构建逻辑不动

## 8. 验收标准

| # | 标准 | 验证方式 |
|---|------|---------|
| 1 | 新增质检记录保存成功后弹出信息窗口 | 手工测试 |
| 2 | 窗口中展示的信息与原版完全一致 | 视觉对比 |
| 3 | 点击确定/Enter/Escape 关闭窗口 | 手工测试 |
| 4 | 窗口居中显示 | 视觉确认 |

## 9. 预估工作量

- 修改 quality_view.py：删除 ~17 行，新增 ~1 行
- 修改 base.py：约 10 行增强
- **净减少代码量：~16 行**

## 10. 方案对比

| 方案 | 优点 | 缺点 | 推荐 |
|------|------|------|:----:|
| **A: 增强 `alert()`** | 复用现有函数，改动集中 | 需扩展 alert 参数 | ⭐ |
| B: 新建 `show_info()` | 独立函数，不影响 alert | 新增代码，增加维护点 | |
