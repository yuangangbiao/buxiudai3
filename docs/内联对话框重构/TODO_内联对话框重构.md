# 内联对话框重构 — 遗留事项

## 验收标准未执行

| # | 标准 | 验证方式 | 状态 |
|---|------|---------|:----:|
| 1 | 所有视图 UI 功能与原版完全一致 | 逐功能手工测试 | ⏳ 待执行 |
| 4 | DAO 层全部使用上下文管理器 | grep "get_connection(" models/*.py = 0 | ⏳ 待检查 |
| 5 | 视图层全部使用 `popup_form` 或 Dialog 类 | 无裸 Toplevel | ⏳ 待检查 |
| 7 | 所有入口、出口、路由、页面文件名、目录名使用英文 | 路径无中文字符 | ⏳ 待检查 |

## quality_view.py 剩余待优化点

### 剩余 2 个内联 Toplevel

| 行号 | 函数 | 说明 | 建议处理方式 |
|:----:|------|------|------------|
| 119 | `_open_quality_rules()` | 打开质量监督规则配置窗口 | 可提取为容器窗口类 |
| 280 | `add_record()` 内 info_win | 保存成功信息展示 | 可复用 `alert()` 或提取为 ResultDisplayDialog |

### 改进建议
- `_open_quality_rules()` 中的 Toplevel 是作为容器承载 `QualityRuleView` 组件，属于合理使用模式，不强制提取
- `info_win`（行280）含 `[FIX-06]` 标记，有注释说明待整体提取时替换为 `center_window()`

## 全项目 Toplevel 分布（当前状态）

剩余 34 个 `tk.Toplevel` 分布在 13 个视图文件中：
- material_prep_view.py: 3 个（已减少 2 个）
- operator_view.py: 5 个
- production_view.py: 4 个
- process_view.py: 2 个
- shipment_view.py: 2 个
- dashboard_view.py: 2 个
- material_rules_view.py: 7 个
- 其余 5 个文件: 各 1 个

## 系统运维提示

### 启动命令
```bash
python mobile_api_ai/dispatch_center.py --port 5003
```

### 运行前检查
- [ ] 确认所有依赖包已安装
- [ ] 确认数据库连接配置正确
- [ ] 确认 `.env` 文件已配置必要环境变量
