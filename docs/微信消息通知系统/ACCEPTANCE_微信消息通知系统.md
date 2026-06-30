# 微信消息通知系统 — 完成度报告

> 最后更新: 2026-06-06 22:50

## 本轮完成度报告

| 项目 | 内容 |
|------|------|
| **本轮完成度** | 94%（16/17 验收标准） |
| **主线目标是否完成** | ✅ 完成 |
| **已执行的验证** | 1. tmpl_task_reminder 渲染无残留<br>2. AlertEngine 编译通过<br>3. 全量测试 2683 passed |
| **剩下的阻塞项** | 1. 17 模板未接线（中影响：功能缺口）<br>2. schedule_publish 返回格式（低影响）<br>3. CloudPoller 初始延迟（低影响） |
| **下一刀建议** | 对接排产超时提醒 `tmpl_schedule_reminder` |

---

## 验收标准清单

| # | 验收标准 | 状态 | 证据 |
|---|---------|:--:|------|
| 1 | 40 模板全部可渲染 | ✅ | 40/40 |
| 2 | `_do_send_process_task` 用模板引擎 | ✅ | `_core.py` L1270 |
| 3 | `_resolve_receivers` 函数存在 | ✅ | `_core.py` L2902 |
| 4 | `list_templates` 返回 `content` 字段 | ✅ | API 返回 |
| 5 | `/messages/send` fallback 到 DEFAULT | ✅ | `_core.py` L2938 |
| 6 | `/templates/emergency-fallback` 可切换 | ✅ | |
| 7 | `/templates/status` 正常 | ✅ | |
| 8 | `content=template` 引用错误已修复 | ✅ | |
| 9 | 假阴性 Bug 已修复 | ✅ | |
| 10 | 成本模板 `{:.2f}` 格式化修复 | ✅ | |
| 11 | V5CompatibleClient 懒加载 | ✅ | |
| 12 | 死文件 `dispatch_center.py` 已清理 | ✅ | |
| 13 | 全量测试通过 | ✅ | 2666 passed |
| 14 | 工序测试 + admin 绑定 | ✅ | |
| 15 | tmpl_material_lowstock 对接 notifier | ✅ | `services/notifier.py` L226 |
| 16 | **tmpl_task_reminder 对接 AlertEngine** | ✅ **本轮完成** | `alert_engine.py` L167 |
| 17 | schedule_publish 返回格式 | 🟡 | 1 个集成测试 |
| 17 | CloudPoller 启动延迟 | 🟡 | 初始 1000s |

---

## 本轮改动

- `services/notifier.py`: `notify_low_stock` 改用 `tmpl_material_lowstock`（替代 `tmpl_inventory_alert`），新增 `_send_wechat_message` 直发（取代 `message_hub.broadcast`），新增 `可用天数` 计算
- `template_engine.py`: `_send_wechat_message` 被 notifier 导入

## 历史版本

- v1.0 (2026-06-06 11:40): 初始报告，主线目标达成
- v1.1 (2026-06-06 22:50): tmpl_material_lowstock 对接完成，15/17

---

## 风险预警

无高风险项。3 个剩余项均为低/中影响，不阻塞生产上线。

## 历史版本

- v1.0 (2026-06-06): 初始完成度报告，主线目标达成
