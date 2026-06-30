# 备料对话框提取 — 对齐文档

## 原始需求
对 `material_prep_view.py` 中的 5 个内联 `tk.Toplevel` 进行对话框提取，复用 `BaseDialog` 基类。

## 边界确认
- **范围**：仅提取**展示/管理型**的 3 个对话框（show_history、_manage_templates、template_preview）
- **排除**：容器型 2 个（open_material_rules、calculate_selected_materials）保留原地
- **不涉及**：备料逻辑修改、数据库模型变更、其他视图文件

## 现有项目理解
- `BaseDialog` 基类已实现（[base.py](file:///d:/yuan/不锈钢网带跟单3.0/views/dialogs/base.py#L813-L881)），5 个模板方法：`_build_ui`/`_validate`/`_on_confirm`/`_on_cancel`/`_on_close`
- `quality_dialogs.py` 已有 3 个继承 BaseDialog 的对话框类可作为模式参考
- `material_prep_view.py` 中 3 个对话框的函数：
  - `show_history()` (L1262) — 纯展示，Treeview + 关闭按钮
  - `_manage_templates()` (L1567) — CRUD 管理，含右键菜单
  - `template_preview` (L1666) — 预览子窗口，仅展示

## 确认事项
- 新增 `material_dialogs.py` 放在 `views/dialogs/` 目录下
- 更新 `views/dialogs/__init__.py` 导出
- 修改 `material_prep_view.py` 替换 3 个函数为对话框调用
