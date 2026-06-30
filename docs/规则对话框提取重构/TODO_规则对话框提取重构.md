# TODO - 规则对话框提取重构

## 待办事项

| # | 事项 | 类型 | 说明 |
|---|------|------|------|
| 1 | ✅ 无待办 | — | 所有任务已完成 |

## 注意事项

- `rule_dialogs.py` 中的 `get_all_param_options_for_quality()` 函数内部导入了 `views.quality_rule_view` 的 helper 函数，保持这种延迟导入模式可避免循环导入
- `MaterialRuleDialog` 接收 `parent, rule, product_type` 三个参数，其中 `rule` 为 `None` 表示新建模式
