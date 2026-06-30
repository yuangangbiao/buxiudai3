# 备料对话框提取 — 验收文档

## 验收日期
2026-05-21

## 验收范围

| 任务 | 描述 | 状态 |
|------|------|:----:|
| **Task 1** | 创建 `material_dialogs.py` — 3 个对话框类 | ✅ 完成 |
| **Task 2** | 更新 `__init__.py` 导出 | ✅ 完成 |
| **Task 3** | 修改 `material_prep_view.py` 替换调用 | ✅ 完成 |
| **Task 4** | 编译验证零错误 | ✅ 完成 |

## 验收标准对照

| # | 标准 | 验证方式 | 结果 |
|---|------|---------|:----:|
| 1 | material_prep_view.py Toplevel 从 5→2 | `grep "Toplevel"` | ✅ 5→2 |
| 2 | 3 个 Dialog 类可独立导入 | `from views.dialogs.material_dialogs import ...` | ✅ 编译通过 |
| 3 | UI 功能与原版完全一致 | emoji/布局/按钮完整保留 | ✅ 已同步 |
| 4 | 编译零错误 | VSCode GetDiagnostics | ✅ 4 文件零错误 |

## 交付物

### 新增文件
| 文件 | 说明 |
|------|------|
| [material_dialogs.py](file:///d:/yuan/不锈钢网带跟单3.0/views/dialogs/material_dialogs.py) | 3 个对话框类，继承 BaseDialog |

### 修改文件
| 文件 | 改动说明 |
|------|---------|
| [__init__.py](file:///d:/yuan/不锈钢网带跟单3.0/views/dialogs/__init__.py) | +2 行导入导出 |
| [material_prep_view.py](file:///d:/yuan/不锈钢网带跟单3.0/views/material_prep_view.py) | 替换 2 个函数为对话框类调用 + 导入 |

### 对话框类清单

| 对话框类 | 基类 | 说明 |
|---------|:----:|------|
| `MaterialPrepHistoryDialog` | BaseDialog | 备料历史记录展示 |
| `MaterialTemplateManagerDialog` | BaseDialog | 模板 CRUD 管理（含右键菜单） |
| `MaterialTemplatePreviewDialog` | BaseDialog | 模板物料预览子窗口 |

## 编译验证

| 文件 | 诊断结果 |
|------|:-------:|
| material_dialogs.py | 0 |
| material_prep_view.py | 0 |
| __init__.py | 0 |
| base.py | 0 |
