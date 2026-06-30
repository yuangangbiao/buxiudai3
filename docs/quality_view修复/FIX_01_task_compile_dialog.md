# FIX-01: `_open_task_compile()` 内联对话框提取

## 1. 问题定位

| 项目 | 内容 |
|------|------|
| **文件** | `views/quality_view.py` |
| **方法** | `QualityView._open_task_compile()` |
| **行号** | 第 112 行 — 第 371 行 |
| **代码量** | ~260 行 |
| **严重度** | 🔴 高 |

## 2. 问题描述

`_open_task_compile()` 方法直接在视图类内部使用 `tk.Toplevel()` 创建了一个完整的质检任务编制对话框，包含：

- 手动创建 Toplevel 窗口（L118-122）
- `main_frame` 的 grid 布局（L124-186）
- 4 个内部嵌套函数：
  - `update_process_options()`（L206-222）— 工单切换时更新工序
  - `update_item_list()`（L224-299）— 工序切换时更新质检项目列表
  - `add_custom_item()`（L281-293）— 添加自定义质检项
  - `generate_task()`（L301-355）— 生成质检任务并保存
- **DAO 层绕过**（L136-149）：直接使用 `get_connection()` 执行原始 SQL

**根本问题**：
1. 对话框逻辑与视图逻辑紧耦合，无法独立测试
2. 260 行代码使视图文件膨胀，可读性差
3. 嵌套函数闭包引用导致代码理解困难
4. 直接 SQL 操作绕过 DAO 层，违反架构分层

## 3. 修复目标

将 `_open_task_compile()` 的整体逻辑提取为独立的 `QualityTaskCompileDialog` 类，放在 `views/dialogs/quality_dialogs.py` 中。视图层只保留一行调用代码。

## 4. 具体实现步骤

### Step 1: 新建 `views/dialogs/quality_dialogs.py` 文件

创建新文件，存放所有质检相关的对话框类。

### Step 2: 定义 `QualityTaskCompileDialog` 类

```python
class QualityTaskCompileDialog:
    """质检任务编制对话框"""
    
    def __init__(self, parent):
        # 1. 创建 Toplevel，设置模态
        # 2. 加载数据（订单列表、工序列表）
        # 3. 调用 build_ui()
        # 4. wait_window()
    
    def _load_work_no_map(self, order_ids):
        """提取原始的 get_connection() SQL 到 DAO 方法"""
        # 调用 QualityDAO.get_work_no_map(order_ids)
        # 该 DAO 方法在 FIX-05 中新增
    
    def build_ui(self):
        """构建 UI：工单选择 + 工序联动 + 质检项目勾选 + 质检类型 + 质检员"""
    
    def _update_process_options(self, event=None):
        """工单切换 → 更新工序下拉选项"""
    
    def _update_item_list(self):
        """工序切换 → 更新质检项目列表（含预设、规则、自定义）"""
    
    def _add_custom_item(self):
        """添加自定义质检项"""
    
    def _generate_task(self):
        """验证输入 → 调用 DAO 保存 → 发送通知 → 关闭对话框"""
    
    def _validate(self):
        """验证必填项"""
```

### Step 3: 改造 `quality_view.py`

将 `_open_task_compile()` 方法替换为：

```python
def _open_task_compile(self):
    """打开任务编制对话框"""
    from views.dialogs.quality_dialogs import QualityTaskCompileDialog
    QualityTaskCompileDialog(self)
    self.load_data()
    self.update_stats()
```

### Step 4: 更新 `views/dialogs/__init__.py`

在 `__init__.py` 中导出新的对话框类。

## 5. 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `views/quality_view.py` | ✅ 修改 | 删除 L112-371，替换为单行调用 |
| `views/dialogs/quality_dialogs.py` | 🆕 新建 | 新增 `QualityTaskCompileDialog` 类 |
| `views/dialogs/__init__.py` | ✅ 修改 | 添加 `QualityTaskCompileDialog` 导出 |
| `models/quality.py` | ✅ 修改（间接） | 依赖 FIX-05 新增的 `get_work_no_map()` |

## 6. 依赖关系

| 前置依赖 | 说明 |
|----------|------|
| **FIX-05**（DAO 层绕过） | `_load_work_no_map()` 需要 FIX-05 提供的 DAO 方法 |
| **FIX-06**（窗口居中） | 使用 `setup_resizable_window()` 替代手动居中 |

## 7. 风险与注意事项

- **UI 一致性**：提取后 UI 布局、字体、颜色必须与原版完全一致
- **工单联动**：工单选择 → 工序联动的交互逻辑不能丢失
- **自定义质检项**：`add_custom_item()` 的动态添加功能需完整保留
- **通知推送**：`generate_task()` 中的 `requests.post` 通知逻辑需保留
- **数据刷新**：保存后需调用 `self.load_data()` + `self.update_stats()`

## 8. 验收标准

| # | 标准 | 验证方式 |
|---|------|---------|
| 1 | 点击"📝 发布任务项编制"按钮，对话框显示正常 | 手工测试 |
| 2 | 工单选择后工序列表联动更新 | 手工测试 |
| 3 | 工序选择后质检项目列表正确显示（预设+规则+自定义） | 手工测试 |
| 4 | 添加自定义质检项功能正常 | 手工测试 |
| 5 | 生成质检任务后数据正确入库 | 检查数据库 |
| 6 | 质检列表自动刷新 | 观察 UI |
| 7 | 无 `tk.Toplevel` 裸创建 | grep 验证 |

## 9. 预估工作量

- 新建文件：~180 行
- 修改 `quality_view.py`：删除 ~255 行，新增 ~8 行
- 修改 `__init__.py`：新增 ~2 行
- **净减少代码量：~250 行**
