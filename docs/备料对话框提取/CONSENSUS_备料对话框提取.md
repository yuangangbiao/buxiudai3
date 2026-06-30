# 备料对话框提取 — 共识文档

## 验收标准
1. `material_prep_view.py` 中内联 Toplevel 从 5 个减至 2 个
2. 3 个新 Dialog 类可独立导入
3. UI 功能与原版完全一致（历史记录、模板管理、模板预览）
4. 编译零错误

## 技术方案
- 新建 `material_dialogs.py`，内含 3 个继承 `BaseDialog` 的类
- `MaterialPrepHistoryDialog` — 历史记录展示，不含确认逻辑
- `MaterialTemplateManagerDialog` — 模板 CRUD（重命名/删除/预览）
- `MaterialTemplatePreviewDialog` — 模板预览子窗口
- 修改 `material_prep_view.py` 中 3 个函数委托新对话框类
- 保留 `open_material_rules()` 和 `calculate_selected_materials()` 原地不动

## 约束
- 必须遵循 `jgs7` 规范：无硬编码、无 sys.path 重复设置、使用 logger
- 数据库操作必须使用 context manager 模式（`get_connection()`）
- 参照 `quality_dialogs.py` 的代码风格
