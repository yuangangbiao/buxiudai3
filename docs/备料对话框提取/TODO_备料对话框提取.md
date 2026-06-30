# 备料对话框提取 — 遗留事项

## 未实施项

| 任务 | 优先级 | 说明 |
|------|:-----:|------|
| Task 2.3: rule_dialogs.py | P2 | quality_rule_view.py + material_rules_view.py 对话框提取 |
| Task 3.1: DAO 连接管理 | P3 | 统一 get_connection_context() |
| material_prep_view.py 剩余 2 个容器型 | — | open_material_rules (L856)、calculate_selected_materials (L1009)，确认保留不处理 |

## 运行验证

```bash
python mobile_api_ai/dispatch_center.py --port 5003
```

手动测试清单：
- [ ] 备料界面 → 历史记录按钮 → 弹出 MaterialPrepHistoryDialog
- [ ] 备料界面 → 模板管理按钮 → 弹出 MaterialTemplateManagerDialog
- [ ] 模板管理 → 右键预览 → 弹出 MaterialTemplatePreviewDialog
- [ ] 模板管理 → 右键重命名 → popup_form 正常工作
- [ ] 模板管理 → 右键删除 → messagebox 确认
