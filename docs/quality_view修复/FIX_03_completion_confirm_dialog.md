# FIX-03: `_show_completion_confirm()` 内联对话框提取

## 1. 问题定位

| 项目 | 内容 |
|------|------|
| **文件** | `views/quality_view.py` |
| **方法** | `QualityView._show_completion_confirm()` |
| **行号** | 第 572 行 — 第 629 行 |
| **代码量** | ~58 行 |
| **严重度** | 🟡 中 |

## 2. 问题描述

`_show_completion_confirm(order_id, selected_order, data, defect_qty)` 是终检合格后弹出的工单完成确认对话框：

- 手动创建 Toplevel（L577-585）
- 手动居中定位（L582-585）
- 布局代码：标题 + 卡片信息 + 提示文字 + 确认/取消按钮（L587-629）
- 2 个内部函数：
  - `do_confirm()`（L612-617）：调用 DAO 完成订单 + 刷新 + 弹提示
  - `do_cancel()`（L619-622）：刷新 + 关闭

**根本问题**：
1. 与 FIX-06 共享完全相同的窗口居中代码（L582-585 vs L556-560）
2. 对话框逻辑与视图方法耦合
3. 此模式在系统中可能多次出现，提取后便于复用

## 3. 修复目标

将 `_show_completion_confirm()` 提取为 `CompletionConfirmDialog` 类，并消除与 FIX-06 的居中代码重复。

## 4. 具体实现步骤

### Step 1: 在 `quality_dialogs.py` 中定义 `CompletionConfirmDialog` 类

```python
class CompletionConfirmDialog:
    """终检完成确认对话框"""
    
    def __init__(self, parent, order_id, order_info, on_confirm_cb=None, on_cancel_cb=None):
        """
        Args:
            parent: 父窗口
            order_id: 订单 ID
            order_info: dict 包含 selected_order, data, defect_qty
            on_confirm_cb: 确认后的回调
            on_cancel_cb: 取消后的回调
        """
        # 1. 创建 Toplevel（使用 setup_resizable_window）
        # 2. 调用 build_ui()
        # 3. wait_window()
    
    def build_ui(self):
        """构建确认对话框 UI"""
        # ✅ 标题区：终检合格
        # ✅ 信息卡片：工单编号、质检类型、结果、不良数量、质检员、时间
        # ✅ 提示文字：确认后的操作说明
        # ✅ 按钮区：确认完成 + 暂不完成
    
    def _on_confirm(self):
        """确认完成 → 调用 DAO 完成订单 → 刷新 → 提示"""
    
    def _on_cancel(self):
        """取消 → 刷新 → 关闭"""
```

### Step 2: 改造 `quality_view.py`

```python
def _show_completion_confirm(self, order_id, selected_order, data, defect_qty):
    """终检合格 -> 弹出工单完成确认框"""
    from views.dialogs.quality_dialogs import CompletionConfirmDialog
    CompletionConfirmDialog(
        parent=self,
        order_id=order_id,
        order_info={
            "selected_order": selected_order,
            "data": data,
            "defect_qty": defect_qty
        },
        on_confirm_cb=lambda: (self.load_data(), self.update_stats()),
        on_cancel_cb=lambda: (self.load_data(), self.update_stats())
    )
```

### Step 3: 更新 `__init__.py`

## 5. 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `views/quality_view.py` | ✅ 修改 | 删除 L572-629，替换为简洁调用 |
| `views/dialogs/quality_dialogs.py` | 🆕 追加 | 新增 `CompletionConfirmDialog` 类 |
| `models/quality.py` | 无 | 已有 `confirm_order_completion()` |

## 6. 依赖关系

| 前置依赖 | 说明 |
|----------|------|
| **FIX-06**（窗口居中） | 使用 `setup_resizable_window()` 统一居中 |
| 无其他 | 可独立进行 |

## 7. 风险与注意事项

- **UI 样式**：提取后的卡片布局、字体、颜色必须与原版一致
- **回调传递**：`on_confirm_cb` 和 `on_cancel_cb` 需要调用 `load_data()` + `update_stats()`
- **order_info 解包**：确保 `selected_order`, `data`, `defect_qty` 正确传递

## 8. 验收标准

| # | 标准 | 验证方式 |
|---|------|---------|
| 1 | 终检合格后弹出确认对话框 | 手工测试：创建终检合格记录 |
| 2 | 确认完成 → 订单状态更新为"已完成" | 检查数据库 |
| 3 | 确认完成 → 自动创建成品入库 | 检查 finished_goods 表 |
| 4 | 暂不完成 → 对话框关闭，无副作用 | 观察 |
| 5 | 对话框位置居中显示 | 视觉确认 |

## 9. 预估工作量

- 追加 quality_dialogs.py：~60 行
- 修改 quality_view.py：删除 ~55 行，新增 ~12 行
- **净减少代码量：~43 行**
