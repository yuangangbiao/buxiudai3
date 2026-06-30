# FINAL — RE-002 消息触发链路修复 · 项目总结

> 阶段 6 收尾 · 交付确认
> 日期: 2026-06-09

## 项目目标

修复不锈钢网带跟单系统"微信消息很多都不触发发送"的问题：
- 报工接口（`/api/sync/report`, `/api/sync/report/actual`）未触发群消息
- 外协发布接口（`/api/sync/outsource/publish`）未触发群消息
- 排产接口（`/api/schedule/submit`, `/api/schedule/confirm`）500 错误

## 根因

1. **MySQLStorage 缺方法**：`schedule_routes.py` 调用 `get_schedule_record_by_order` 等方法，MySQLStorage 未实现 → 排产 500
2. **MySQLStorage 缺表**：`schedule_records` 表未建 → DDL 缺失
3. **sync_bp 缺消息调用**：`/report` `/report/actual` `/outsource/publish` 主业务完成后未触发 `bot.send_markdown`

## 修复内容

| 修复点 | 文件 | 性质 |
|:-------|:-----|:-----|
| 新增 `schedule_records` 表 DDL | `mobile_api_ai/storage/mysql_storage.py` | 数据库 |
| 补 5 个 ScheduleStorageMixin 方法 | 同上 | 业务逻辑 |
| 补 2 个 ScheduleFlowMixin 方法 | 同上 | 业务逻辑 |
| `/report` 补群消息调用 | `mobile_api_ai/sync_bp.py` | 业务逻辑 |
| `/report/actual` 补群消息调用 | 同上 | 业务逻辑 |
| `/outsource/publish` 补群消息调用 | 同上 | 业务逻辑 |
| 新增 `tmpl_report_actual` 模板 | `mobile_api_ai/template_engine.py` | 配置 |

## 影响范围

- **数据库**：1 张新表（`schedule_records`），可重入
- **API**：3 个本地 5003 端点行为增强（消息发送），无破坏性变更
- **模板**：1 个新模板 ID
- **依赖**：复用现有 `bots.factory` + `template_engine`，无新增依赖

## 风险

- **极低**：所有消息调用 `try/except Exception` 包裹，失败仅 log
- **零回归**：路由基线无变化
- **可回滚**：DDL 有 `DROP TABLE IF EXISTS` 回滚语句

## 后续

- 已通过 P6 悲观审计（700/700）
- 已通过 P7 零回归检查
- 端到端测试脚本：`tests/test_re002_message_trigger.py`
- 上线重启 `dispatch_center.py --port 5003` 即可生效
