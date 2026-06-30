# ALIGNMENT — RE-002 报工/排产/修改报工等业务接口未触发微信消息

> 阶段 1: Align · 项目特性规范 + 边界确认 + 需求理解
> 日期: 2026-06-09
> 任务来源: 实时排查（用户反馈"报工、修改报工等任务发布，排产等都没有触发微信消息发送"）
> 优先级: P0 阻断

---

## 一、项目上下文分析

### 1.1 技术栈
- **后端**: Python 3.14 + Flask 2.3.3 + pymysql + DBUtils
- **入口**: 
  - `mobile_api_ai/app.py`（单文件 ~1700 行）
  - `mobile_api_ai/dispatch_center.py`（端口 5003，调度中心）
- **存储**: 主库 `steel_belt`（MySQL InnoDB），容器库 `container_center`（MySQL InnoDB）
- **企业微信**: 本地 → 云端 5006（wechat_cloud.py）→ 企业微信
  - 应用消息: `POST /api/wechat/send`（`@all`/指定 user）
  - 群机器人: `POST /api/wechat/proxy_send`（带 `_webhook_url` 字段）

### 1.2 现有代码模式
- 消息发送两条路径：
  1. **应用消息**（`_send_wechat_message` in `template_engine.py:383`）→ `send_to_cloud` → 云端 5006 `/api/wechat/send`
  2. **群机器人**（`GroupBot.send_markdown` in `bots/group_bot.py:111`）→ 云端 5006 `/api/wechat/proxy_send`，降级直连
- 调度中心核心业务路由: `mobile_api_ai/dispatch_center/_core.py`（含 `advance_process`、`save_schedule_record` 等）
- 同步/报工路由: `mobile_api_ai/sync_bp.py`（含 `/api/sync/report`、`/api/sync/outsource/publish`）
- 排产路由: `mobile_api_ai/dispatch_center/schedule_routes.py`（含 `/api/schedule/submit`、`/api/schedule/confirm`）
- 存储: 调度中心用 `storage.mysql_storage.MySQLStorage`（由 `StorageFactory` 创建）

### 1.3 业务域
- **报工**: 工序完成后，操作员上报数量 → `/api/sync/report` 或 `/api/sync/report/actual` → 累加 `completed_qty`
- **修改报工**: 管理员后台修正报工 → app.py 中事务（RE-001 已规划）
- **排产**: 工单分阶段流转（`schedule_routes.py` 4 阶段：publish/submit/confirm）
- **消息通知场景**:
  - 排产待处理 → 提醒生产部
  - 排产已提交 → 通知客户/桌面端
  - 排产已确认/已拒绝 → 通知相关方
  - 报工完成 → 通知生产部/客户
  - 外协任务发布 → 通知外协商

---

## 二、原始需求

> **RE-002**: 报工、修改报工、排产等业务接口未触发微信消息

**问题表现**（已实测 2026-06-09）：

| 接口 | 路径 | 状态 | 现象 |
|:-----|:-----|:-----|:-----|
| 排产 submit | `POST /api/schedule/submit` | ❌ 500 | `'MySQLStorage' object has no attribute 'get_schedule_record_by_order'` |
| 排产 confirm | `POST /api/schedule/confirm` | ❌ 500 | 同上（storage 缺方法） |
| 报工 report | `POST /api/sync/report` | ⚠️ 200 但**无消息** | 代码无 `_send_wechat_message` 调用 |
| 报工 actual | `POST /api/sync/report/actual` | ⚠️ 200 但**无消息** | 同上 |
| 外协 publish | `POST /api/sync/outsource/publish` | ⚠️ 200 但**无消息** | 同上 |
| 流程 advance | `POST /api/dispatch-center/processes/advance` | ✅ | 有 `_notify_process_event` 调用 |
| 显式 send | `POST /api/dispatch-center/messages/send` | ✅ | 链路正常，群消息发送成功 |
| 云端 proxy | `POST http://124.223.57.82:5006/api/wechat/proxy_send` | ✅ | 返回 `{"errcode":0,"errmsg":"ok"}` |

**根因（已定位）**：
1. **MySQLStorage 缺少 ScheduleStorageMixin / ProcessStorageMixin**——`storage/mysql_storage.py:60-940` 仅独立实现 5 个方法，缺 9 个排产/工序方法
2. **sync_bp.py 三个端点无消息发送**——`/report`、`/report/actual`、`/outsource/publish` 只更新 work_order 文档，**完全没有 `_send_wechat_message` / `bot.send_markdown` 调用**

---

## 三、边界确认（任务范围）

### ✅ 包含
1. **MySQLStorage 补全排产/工序方法**：混入 `ScheduleStorageMixin` + `ProcessStorageMixin`，覆盖所有调用
2. **sync_bp.py 报工类端点补消息发送**：
   - `/api/sync/report` → 报工完成通知（`tmpl_report_submitted`）
   - `/api/sync/report/actual` → 实际报工通知（`tmpl_report_actual`）
   - `/api/sync/outsource/publish` → 外协发布通知（`tmpl_outsource_send`）
3. **消息通道统一**：复用 `bots.factory.get_factory().get_group_bot()`（与 `_core.py` 现有模式一致）
4. **失败不影响主业务**：消息发送失败仅打 log，不阻断主流程（与现有 `_core.py:692` 一致：`logger.warning(f"[Schedule] 发送微信通知失败: {e}")`）
5. **单测覆盖**：5+ 个新单测（每个端点至少 1 个 + storage 2 个）

### ❌ 不包含
1. RE-001（history 事务包裹）——独立任务，不动
2. 排产流程的 UI 层消息模板调整——独立 UX 任务
3. 消息模板本身（`tmpl_*`）的内容修改——不在本任务范围
4. Webhook URL / Corp ID 等企业微信凭据更新——已由前置任务配置完成
5. 群机器人新增/重命名——配置项已固化

---

## 四、需求理解（对现有项目的理解）

### 4.1 影响点精确定位

| 文件 | 路径 | 影响点 |
|:-----|:-----|:------|
| `storage/mysql_storage.py` | `L60-940` | 缺 `get_schedule_record_by_order` 等 9 个方法 |
| `sync_bp.py` | `L94-220` | `/report`、`/report/actual` 缺消息调用 |
| `sync_bp.py` | `L224-288` | `/outsource/publish` 缺消息调用 |
| `dispatch_center/schedule_routes.py` | `L609-707` | `submit` 调 `get_schedule_record_by_order` 必 500 |
| `dispatch_center/schedule_routes.py` | `L708-816` | `confirm` 同上 |
| `template_engine.py` | `L383-397` | `_send_wechat_message` 已有，可直接复用 |

### 4.2 关键设计点
- **存储层一致性**: `storage_layer.py:204-310` 的 Mixin 接口已稳定，MySQLStorage 继承即可，无需重写
- **消息发送容错**: 参考 `schedule_routes.py:690-692` 现有模式，try/except + logger.warning 包裹，不抛异常给主业务
- **群机器人 vs 应用消息**: 全部走群机器人（`bot.send_markdown`），与 `_core.py:1457-1463` 的 `tmpl_process_start` 通知保持一致

### 4.3 风险点
- **DDL**: 无（不涉及表结构变更）
- **公共API扩展**: `MySQLStorage` 新增 9 个方法，调用方需兼容——已确认所有调用方都在 `dispatch_center/schedule_routes.py`
- **消息发送失败**: 网络抖动/云端5006宕机时不应阻塞报工主流程——必须 try/except
- **并发**: 报工接口本身已有 `get_sub_step_summary` 的 30秒去重（业务层），消息发送无并发风险
- **现有测试**: `tests/integration/test_cc_aux.py` 等可能用到 storage mock，需保证兼容

---

## 五、疑问澄清（已与用户确认）

| 决策点 | 选定方案 | 用户确认 |
|:-------|:--------|:--------|
| 修复方向 | **方案A**：MySQLStorage 补方法 + sync_bp 三端点补消息 | ✅（用户回复"方案A"） |
| 消息通道 | 群机器人（`bot.send_markdown`），与 `_core.py` 现有模式一致 | 推论（与现状一致，无需另问） |
| 失败处理 | 消息失败仅打 log，不阻断主流程 | 推论（与 `schedule_routes.py:692` 一致） |
| 走 6A 完整流程 | 写 ALIGNMENT + DESIGN + TASK 文档后等签字 | 用户打开了 `ALIGNMENT_RE-001.md` 表明走此流程 |

### 待用户最终确认项
1. 文档签字：本文档是否符合预期？（如同意，签字后进入阶段 2 架构设计 `DESIGN_RE-002.md`）
2. 排产/报工消息通知的目标接收人：默认**群机器人**（全员），是否需要按角色（生产部/客户）分流？——可暂留默认，实施中再细化

---

## 六、最终共识（待用户签字后生效）

### 6.1 验收标准
- [ ] MySQLStorage 混入 `ScheduleStorageMixin` + `ProcessStorageMixin`，9 个方法可用
- [ ] `/api/sync/report` 报工完成后触发 `tmpl_report_submitted` 群消息
- [ ] `/api/sync/report/actual` 实际报工触发 `tmpl_report_actual` 群消息
- [ ] `/api/sync/outsource/publish` 外协发布触发 `tmpl_outsource_send` 群消息
- [ ] 排产 `/api/schedule/submit` 不再 500，能成功写入 + 发消息
- [ ] 排产 `/api/schedule/confirm` 不再 500，能成功确认/拒绝 + 发消息
- [ ] 消息发送失败时主业务返回 200（仅 log warning）
- [ ] 现有 5+ 个 storage 集成测试不挂

### 6.2 质量门控
- [ ] 单测覆盖率：sync_bp 三端点 100% 路径覆盖
- [ ] 边界测试：消息发送抛异常 → 主流程仍返回 200
- [ ] 集成测试：schedule submit/confirm 完整链路跑通
- [ ] 路由基线对比：既有路由无删除/修改

### 6.3 实施原则
- 严格遵循项目现有 `with conn.cursor() as c` 模式
- 复用 `bots.factory.get_factory().get_group_bot()` 单例
- 失败必须 `logger.warning` 记录，不抛异常给主业务
- 文档、代码、测试三件套同步产出
- 现有 `test_dispatch_substeps.py` 等测试不挂

---

## 七、任务依赖与并行关系

```
RE-002 消息触发链路修复
├── 依赖：✅ 无前置（独立任务，但与 RE-001 history 事务包裹正交）
├── 后续：RE-011 异人通知（依赖消息链路打通）
├── 并行：RE-002 乐观锁、RE-005 WAL 预写日志（独立）
└── 阻塞：RE-014 排产流程 UI 优化（依赖消息通知可见）
```

---

## 八、风险与回退

| 风险 | 概率 | 影响 | 回退方案 |
|:-----|:----:|:----:|:---------|
| MySQLStorage 继承 Mixin 后方法签名冲突 | 低 | 中 | 遇到冲突方法改用 mixin 默认实现（已有 `fetch_one`/`update`/`insert` 等基类方法） |
| 报工消息发送阻塞主流程 | 低 | 高 | 严格 try/except 包裹，验证失败仅 log |
| 现有 storage 集成测试失败 | 中 | 中 | 逐个修复 mixin 引入的兼容问题 |
| 群机器人消息频率触发企业微信限流 | 低 | 中 | 报工场景单条消息，不构成限流风险 |
| 排产 confirm 业务逻辑回归 | 中 | 高 | 集成测试覆盖完整 4 阶段流程 |

---

## 九、本轮完成度报告

| 项目 | 内容 |
|:-----|:-----|
| **本轮完成度** | 20%（仅完成对齐阶段） |
| **主线目标是否完成** | ⏳ 对齐阶段已完成，等待用户签字 |
| **已执行的验证** | 1. 链路验证 ✅（云端5006 / 5003 messages/send 链路通）<br>2. 接口定位 ✅（8 个接口实操 200/500/无消息 状态全部确认）<br>3. 根因定位 ✅（MySQLStorage 缺方法 + sync_bp 缺消息调用 双根因） |
| **剩下的阻塞项** | 1. 文档签字（待用户过审 ALIGNMENT）<br>2. DESIGN + TASK 文档待写 |
| **下一刀建议** | 用户签字后，进入阶段 2 架构设计（DESIGN_RE-002.md），输出 mixin 引入方案 + sync_bp 三端点消息调用模板 + 消息容错设计 |

---

**说明**：
- 本文档为阶段 1 对齐产物，签字后冻结
- 阶段 2 架构设计将基于本文档输出 `DESIGN_RE-002.md`
- 阶段 3 任务拆分将基于 DESIGN 输出 `TASK_RE-002.md` 原子化任务清单
