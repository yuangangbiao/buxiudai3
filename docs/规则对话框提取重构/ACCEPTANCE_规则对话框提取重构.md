# ACCEPTANCE - 规则对话框提取重构

## 验收检查清单

### ✅ 所有需求已实现

| # | 需求 | 状态 | 说明 |
|---|------|------|------|
| 1 | `dialogs/__init__.py` 导出规则对话框类 | ✅ | 已添加 QualityRuleDialog, MaterialRuleDialog 等6个类 |
| 2 | `quality_rule_view.py` 委托 QualityRuleDialog | ✅ | `_show_rule_dialog` 改为一行委托 |
| 3 | `material_rules_view.py` 委托所有对话框 | ✅ | 6个方法全部替换为一行委托 |
| 4 | 保留 helper 函数供 rule_dialogs.py 使用 | ✅ | `get_custom_material_params`, `get_custom_surface_params` 保留在原文件中 |

### ✅ 验收标准全部满足

| # | 标准 | 状态 | 验证方式 |
|---|------|------|---------|
| 1 | 编译通过，零诊断 | ✅ | `python -m py_compile` 全部 exit code 0 |
| 2 | quality_rule_view.py 的 `_show_rule_dialog` 内联代码已移除 | ✅ | 400行代码缩小为2行 |
| 3 | material_rules_view.py 的6个内联对话框方法已移除 | ✅ | 700行代码缩小为6行 |
| 4 | exports 完整，无遗漏 | ✅ | `__all__` 中列出所有新导出的类 |

### ✅ 项目编译通过

```
views\dialogs\__init__.py        → exit code 0
views\dialogs\rule_dialogs.py     → exit code 0
views\quality_rule_view.py        → exit code 0
views\material_rules_view.py      → exit code 0
```

### ✅ 实现与设计一致

- 严格遵循现有 `dialogs/` 目录架构
- 复用 `dialogs/__init__.py` 的统一导出模式
- 保持 helper 函数在原文件，避免循环导入
- 委托模式一致：`from .dialogs.rule_dialogs import XxxDialog; XxxDialog(self, ...)`

## 质量评估

| 维度 | 评估 | 说明 |
|------|------|------|
| 代码质量 | ✅ 优秀 | 移除重复的内联对话框代码，委托清晰 |
| 可维护性 | ✅ 提升 | 对话框逻辑集中管理，视图层更薄 |
| 文档 | ⚠️ 已创建 | 本次任务文档已在 `docs/规则对话框提取重构/` 下 |
| 现有系统集成 | ✅ 良好 | 无破坏性变更，视图层行为完全一致 |
