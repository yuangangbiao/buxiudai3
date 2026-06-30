# FIX-02: `_open_qc_form()` 内联对话框提取 + 闭包嵌套解耦

## 1. 问题定位

| 项目 | 内容 |
|------|------|
| **文件** | `views/quality_view.py` |
| **方法** | `QualityView._open_qc_form()` |
| **行号** | 第 681 行 — 第 864 行 |
| **代码量** | ~184 行 |
| **严重度** | 🔴 高 |

## 2. 问题描述

`_open_qc_form(record_id, values, row_id)` 是一个质检内容填写对话框，包含：

- 手动创建 Toplevel 窗口（L686-690）
- grid 动态布局质检项目输入行（L695-735）
- **3 层闭包嵌套**：

```
第一层: on_check(check_var, item_name)     L737-745
   └── 控制输入框/附件的启用/禁用状态

第二层: add_attachment(target_var)          L795-807
   └── 弹出文件选择对话框 + 文件大小校验

第三层: do_save()                           L812-857
   └── 数据验证 → DAO.update → 更新 TreeView → 关闭
```

**根本问题**：
1. 3 层闭包嵌套导致代码逻辑难以追踪和维护
2. 184 行内联代码使视图膨胀
3. 闭包引用了大量外部变量（`item_*_vars`, `inspector_var` 等），出现幽灵变量的风险
4. `do_save()` 中同时处理了数据验证、DAO 操作、UI 更新，违反单一职责

## 3. 修复目标

将 `_open_qc_form()` 提取为独立的 `QualityRecordFormDialog` 类，将 3 层闭包解耦为类方法。

## 4. 具体实现步骤

### Step 1: 在 `quality_dialogs.py` 中定义 `QualityRecordFormDialog` 类

```python
class QualityRecordFormDialog:
    """质检内容填写对话框"""
    
    def __init__(self, parent, record_id, values, row_id=None, tree=None, update_stats_cb=None):
        # 1. 保存参数
        # 2. 创建 Toplevel
        # 3. 调用 build_ui()
        # 4. wait_window()
    
    def build_ui(self):
        """构建 UI：工单信息显示 + 质检项目行 + 质检员 + 结果 + 不良 + 备注"""
    
    def _on_check(self, item_name):
        """方法级代替闭包：勾选/取消勾选时控制输入框状态"""
    
    def _add_attachment(self, target_var):
        """方法级代替闭包：文件选择 + 大小校验"""
    
    def _validate(self):
        """方法级代替闭包：验证必填项"""
        # 1. 质检员不为空
        # 2. 至少勾选一个质检项
        # 3. 已勾选项必须填写结果
    
    def _do_save(self):
        """方法级代替闭包：保存数据"""
        # 1. 收集所有表单数据
        # 2. QualityDAO.update()
        # 3. 更新 TreeView 显示（如果有 callback）
        # 4. 关闭对话框
        # 5. 调用 update_stats_cb()
```

### Step 2: 闭包解耦方案

| 原闭包 | 新方法 | 解耦方式 |
|--------|--------|---------|
| `on_check(v, n)` L737-745 | `QualityRecordFormDialog._on_check(item_name)` | lambda | 
| `add_attachment(v)` L795-807 | `QualityRecordFormDialog._choose_file()` | 类方法 |
| `do_save()` L812-857 | `QualityRecordFormDialog._do_save()` | 类方法 |

闭包中引用的外部变量全部转为实例属性（`self.item_check_vars`, `self.inspector_var` 等）。

### Step 3: 改造 `quality_view.py`

```python
def _open_qc_form(self, record_id, values, row_id=None):
    """打开质检内容填写对话框"""
    from views.dialogs.quality_dialogs import QualityRecordFormDialog
    dialog = QualityRecordFormDialog(
        parent=self,
        record_id=record_id,
        values=values,
        row_id=row_id,
        tree=self.tree,
        update_stats_cb=self.update_stats
    )
```

### Step 4: 更新 `__init__.py`

## 5. 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `views/quality_view.py` | ✅ 修改 | 删除 L681-864，替换为单行调用 |
| `views/dialogs/quality_dialogs.py` | 🆕 追加 | 新增 `QualityRecordFormDialog` 类 |

## 6. 依赖关系

| 前置依赖 | 说明 |
|----------|------|
| **FIX-06**（窗口居中） | 使用 `setup_resizable_window()` 替代手动居中 |
| 无其他 | 可独立进行 |

## 7. 风险与注意事项

- **动态行生成**：L711-735 的循环动态生成质检项输入行，提取后需保持完全一致
- **文件附件**：`add_attachment` 中的 `filedialog.askopenfilename()` 和文件大小校验需保留
- **TreeView 更新**：`do_save()` 中直接操作 `self.tree.item()` 更新行显示，需通过回调传入
- **快捷键绑定**：L567-568 的 Enter/Escape 快捷键需保留
- **`setup_resizable_window`**：需确认 `window_key` 不与其他对话框冲突

## 8. 验收标准

| # | 标准 | 验证方式 |
|---|------|---------|
| 1 | 右键菜单 → "填写内容" 打开对话框 | 手工测试 |
| 2 | 质检项目行动态显示，勾选后输入框/附件启用 | 手工测试 |
| 3 | 文件选择功能正常，超过 2M 提示错误 | 手工测试 |
| 4 | 保存后数据正确写入数据库 | 检查数据库 |
| 5 | TreeView 行显示即时更新 | 观察 UI |
| 6 | 对话框关闭后 stats 区域更新 | 观察 UI |
| 7 | 无裸 `tk.Toplevel` 创建 | grep 验证 |

## 9. 预估工作量

- 追加 quality_dialogs.py：~150 行
- 修改 quality_view.py：删除 ~180 行，新增 ~10 行
- **净减少代码量：~170 行**
