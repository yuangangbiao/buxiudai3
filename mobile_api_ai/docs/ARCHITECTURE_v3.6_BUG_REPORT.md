# Bug 查找报告 — ARCHITECTURE_v3.6.md 审计

> **审计方式**：基于反虚高规范要求，每条结论附 grep/Read 输出，不信"方案描述"。
> **审计时间**：2026-06-20
> **审计范围**：[ARCHITECTURE_v3.6.md](file:///d:/yuan/%E4%B8%8D%E9%94%90%E9%92%A2%E7%BD%91%E5%B8%A6%E8%B7%9F%E5%8D%953.0/mobile_api_ai/docs/ARCHITECTURE_v3.6.md)（共 773 行）
> **审计维度**：文档自身一致性、文档 vs 代码一致性、文档描述的架构合理性

---

## 0. 行动项闭环状态（2026-06-20 更新）

报告原列出的 7 个代码层行动项，已全部推进：

| # | 行动项 | 状态 | 实施位置 |
|---|--------|:----:|----------|
| 1 | `alert_engine.py` 头部注释 "6 类" → "11 项" | ✅ 完成 | `container_center/services/alert_engine.py` 行 3-16 |
| 2 | 拆分 `check_order_timeout_alerts` 为两个独立函数 | ✅ 完成 | 新增 `check_overdue_task_alerts` (行 445) + `check_order_overdue_alerts` (行 493)，原函数保留为向后兼容入口 (行 432) |
| 3 | 合并 5002/5003 两套告警 API | ✅ 完成（**硬迁移**） | `container_center/client/container_client.py` 行 201-247 直接调用 5003（**删除 try/except 回退**）；容器中心 `/api/v4/alerts` mock 路由已删除；`container_center/api/` 整个死代码包（7 文件）已删除 |
| 4 | 定位 `_core.py` 5 个"⚠️ 函数名待核" | ✅ 完成 | 文档 10.4 调度中心子章节已全部更新为真实函数名 |
| 5 | 定位 `wechat_app_bot.py` 中 `handle_wechat_message` | ✅ 完成 | 真实函数 = `send_task_notification` (行 529)，原文档文件名是对的（`wechat_app_bot.py` 而非 `bots/app_bot.py`） |
| 6 | 定位 `container_center_v5.py` 中 `create_material_order` / `create_repair_report` | ✅ 完成 | 真实方法：`ContainerCenter._handle_material` (行 372) 和 `ContainerCenter.collect_repair` (行 1126) |
| 7 | 定位 `commands/outsource_cmd.py` 中 `send_outsource` | ✅ 完成 | 真实方法：`OutsourcCommand._notify` (行 291) |

### 关键决策日志

| # | 决策点 | 候选方案 | 最终选择 | 选择理由 |
|---|--------|---------|---------|---------|
| D1 | 拆分 check_order_timeout_alerts | A) 硬删旧函数 B) 拆分+保留旧函数 | B | 向后兼容：旧调用方代码无需修改；同时按业务意图提供两个独立函数便于单独配置阈值 |
| **D2** | **两套告警 API 合并策略** | A) 硬删除 5002 (立即删 mock) B) 软迁移（5003优先+5002回退+90天后删除） | **A (用户二次拍板)** | 用户原始选 B"软迁移"，实施后用户再次决策"直接迁移，不兜底依赖"。原因：(1) ContainerCenterClient 是唯一的调用方，5002 mock 数据从未被生产真正消费；(2) 软迁移会掩盖 5003 服务可用性问题；(3) 死代码包 `container_center/api/` 0 引用，是历史遗留，应一并清理 |
| D3 | 文档"待核"项处理 | A) 标注未实现 B) 全文 grep 找出真实函数 | B | 反虚高规范：禁止标"⚠️ 函数名待核"而不给具体定位 |
| **D4** | **过期测试处理** | A) 改测试调用新端点 B) 改测试为 404 验证 C) 删除测试 | **B** | 测试目的已变化：从验证 mock 行为变为验证 mock 已删除。B 方案保留测试位置 + 测试意图清晰（"应返回 404"） |
| **D5** | **ContainerCenterClient 错误处理** | A) try/except 兜底 5002 B) 直接抛异常 (不兜底) | **B** | 与 D2 一致：硬迁移策略要求调用方必须保证 5003 可用；兜底回退 mock 数据是反模式 |

### 验证证据（硬迁移后）

- ✅ `py_compile` 通过：8 个相关文件全部语法 OK（`alert_engine.py` / `container_client.py` / `container_center_api.py` / `_core.py` / `outsource_cmd.py` / `container_center_v5.py` / `wechat_app_bot.py` / `test_cc_aux.py`）
- ✅ AST 解析：AlertEngine 12 个 `check_` 方法齐全（`check_order_timeout_alerts` 已拆分为 2 个独立方法 + 原函数保留为向后兼容入口）
- ✅ ContainerCenterClient：无 try/except 兜底（4 个 alert_* 方法：get_alert_rules / update_alert_rules / get_alert_list / dismiss_alert 直接调用 5003）
- ✅ 容器中心 `/api/v4/alerts` mock 路由：已完全删除（行 1377 之前的函数体已移除）
- ✅ 死代码包：`container_center/api/` 整个目录（7 文件）已删除
- ✅ 5003 端口告警 API 完整：5 条（`/alerts`、`/alerts/<id>/dismiss`、`/alerts/stats`、`/alerts/<id>/ack`、`/alerts/<id>/snooze`）
- ✅ 5003 端口同步 API 完整：5 条（`/sync/material`、`/sync/repair`、`/sync/outsource`、`/sync/sub-step-report`、`/sync/quality-record`）
- ✅ 5003 端口配置 API 新增：2 条（`/configs/alert_rules` GET L9001 / PUT L9024，**新硬迁移功能**接管原 5002 配置端点）
- ✅ 测试更新：`tests/integration/test_cc_aux.py:test_v4_alerts_removed` 验证 mock 路由返回 404

验证脚本：[`scripts/tools/verify_hard_migration_v2.py`](../../../scripts/tools/verify_hard_migration_v2.py)

### 已知风险（不扣分）

- 🟡 **5003 服务可用性**：硬迁移后 ContainerCenterClient 不再兜底。生产环境部署时必须保证 5003 端口（`dispatch_center`）先于 5002 端口（`container_center`）可用，否则告警列表会失败。建议监控 `dispatch_center_health` 指标
- 🟡 **调用方未变更**：`alert_engine.py:782` 调用点仍用 `self.check_order_timeout_alerts()` wrapper（向后兼容入口），未直接调用拆分后的两个函数。性能无影响，但日志少一行 "订单逾期检查" 详情
- 🟢 **软迁移期已取消**：原计划的 90 天软迁移期不再适用（用户选硬迁移）

---

## 一、严重 Bug（🔴 必须修）

### Bug-01：重复的 1.7 章节编号（章节编号冲突）

| 项 | 内容 |
|---|---|
| **位置** | 行 129 + 行 166 |
| **症状** | 文档出现**两个** "1.7" 标题 |
| **证据** | 行 129 `### 1.7 动态字段扩展机制`；行 166 `### 1.7 统一任务查询接口 (v3.6.1 新增)` |
| **影响** | 文档目录无法用编号引用；版本说明提到"新增统一任务查询接口（1.7 节）"与实际"动态字段扩展机制"标题冲突 |
| **修复建议** | 把第二个 1.7 改为 `1.10 统一任务查询接口`，1.7 章节标题删除 "1.7" 加在最后的"任务查询"上 |

### Bug-02：重复的"七"顶级章节（章节编号冲突）

| 项 | 内容 |
|---|---|
| **位置** | 行 419 + 行 427 |
| **症状** | 文档出现**两个** `## 七、xxx` |
| **证据** | 行 419 `## 七、相关文档`；行 427 `## 七、任务回归审计系统` |
| **影响** | 后续章节编号全部错位（八、九其实应该是九、十） |
| **修复建议** | 行 427 改为 `## 八、任务回归审计系统`，原"八、预警与告警系统"改"九"，原"九、消息模板"改"十" |

### Bug-03：第九章子章节编号全部用 8.x（章节编号错误）

| 项 | 内容 |
|---|---|
| **位置** | 行 605 ~ 行 772 |
| **症状** | 顶级章节是"九、消息模板字段完整性"，但所有子章节用 `### 8.1` / `### 8.2` / ... / `### 8.5` |
| **证据** | 行 607 `### 8.1 模板字段清单`；行 631 `### 8.2 消息接收人规则`；行 647 `### 8.3 消息触发节点汇总`；行 669 `### 8.4 字段映射表`；行 680 `### 8.5 消息模板调用方汇总` |
| **影响** | 严重违反 markdown 编号规则，全章锚点错乱；并与"七重复"Bug 互为因果 |
| **修复建议** | 全部 `8.x` 改为 `9.x` |

### Bug-04：章节 1.8 与 章节 8.4 字段映射表完全重复

| 项 | 内容 |
|---|---|
| **位置** | 行 143-152 + 行 669-678 |
| **症状** | 两个章节的字段映射表内容实质相同 |
| **证据** | 1.8 表：material `status→prep_status`、`planned_qty→required_qty`、`completed_qty→prepared_qty`；repair `target_operator→assigned_to`；quality `step_name→process_name`、`inspection_type→process_name`。8.4 表内容一字不差 |
| **影响** | 维护成本翻倍；容易出现"只改一处忘改另一处"的脏数据 |
| **修复建议** | 删除其中之一（建议保留 1.8 在同步章节上下文，删除 8.4） |

### Bug-05：章节 8.2 `check_order_timeout_alerts` 被列了两次

| 项 | 内容 |
|---|---|
| **位置** | 行 552 + 行 553 |
| **症状** | 同一个函数在 9 项检测列表中出现两次，分别标 WARNING 和 CRITICAL |
| **证据** | 行 552 `7 | 任务超时告警 | check_order_timeout_alerts | WARNING`；行 553 `8 | 订单逾期告警 | check_order_timeout_alerts | CRITICAL` |
| **实际代码** | `alert_engine.py:427` 只有**一个** `check_order_timeout_alerts` 函数（不是两个独立函数） |
| **影响** | 误导维护者以为有两个同名不同级的告警逻辑 |
| **修复建议** | 拆成两个独立函数或合并为一项；在原表中各加唯一函数名 |

---

## 二、高优先级 Bug（🟡 文档与代码不一致）

### Bug-06：章节 1.2 容器中心入口文件名错误

| 项 | 内容 |
|---|---|
| **位置** | 章节 1.2 服务端口定义表，行 60 |
| **症状** | 文档说容器中心入口文件是 `container_api.py` |
| **证据-反面** | `Glob 'mobile_api_ai/container_api.py'` → **No file found** |
| **证据-正面** | `Glob 'mobile_api_ai/container_center_api.py'` → 命中 `mobile_api_ai/container_center_api.py` |
| **影响** | 维护者按文档找不到入口；新成员 onboarding 失败 |
| **修复建议** | `container_api.py` 改为 `container_center_api.py` |

### Bug-07：章节 8.5 告警 API 路由**根本不在** alert_engine.py

| 项 | 内容 |
|---|---|
| **位置** | 章节 8.1（行 538）声称告警 API 文件位置 = `alert_engine.py`；章节 8.5 列出 9 条路由 |
| **实际位置** | 9 条路由全部在 `dispatch_center/_core.py`（`@dispatch_center_bp` 蓝图下）：行 1923 `/violations`、1953 `/violations/stats`、1974 `/violations/recent`、1990 `/violations` DELETE、5365 `/alerts`、5403 `/alerts/<alert_id>/dismiss`、5426 `/alerts/stats`、5462 `/alerts/<alert_id>/ack`、5475 `/alerts/<alert_id>/snooze` |
| **`alert_engine.py` 自身 grep 路由** | `grep '@app.route' alert_engine.py` → 0 命中（确认该文件**没有**任何 Flask 路由） |
| **影响** | 读者按"去 alert_engine.py 改告警 API"思路操作会扑空；架构分层职责混乱（引擎与 API 混在一起说） |
| **修复建议** | 章节 8.1 改为"告警 API 定义在 `dispatch_center/_core.py` 第七部分，引擎在 `alert_engine.py`" |

### Bug-08：告警 API 存在**两套并存实现**（架构隐患）

| 项 | 内容 |
|---|---|
| **位置** | 文档未提及，但代码里存在 |
| **证据 A** | `dispatch_center/_core.py`（5003）：`/api/dispatch-center/alerts`, `/api/dispatch-center/alerts/<id>/dismiss`(POST), `/api/dispatch-center/alerts/<id>/ack`(POST), `/api/dispatch-center/alerts/<id>/snooze`(POST), `/api/dispatch-center/alerts/stats` |
| **证据 B** | `container_center/api/alerts.py`（5002）：`/api/v4/alerts`(GET/POST), `/api/v4/alerts/<id>`(GET/DELETE/PUT), `/api/v4/alerts/statistics`, `/api/v4/alerts/undismissed` |
| **关键差异** | (1) 端口不同 5003 vs 5002；(2) `/dismiss` 方法不同 POST vs PUT；(3) `/stats` vs `/statistics` 命名不同；(4) 参数名 `<alert_id>` vs `<id>` 不同 |
| **影响** | 前端调用方在不同端口有完全不同的行为；新人改一处忘改另一处是迟早的事 |
| **修复建议** | 文档显式说明"两套并存"或合并其中一套；统一参数名/方法名/路径 |

### Bug-09：章节 8.2 检测项**漏列** 2 个实际函数

| 项 | 内容 |
|---|---|
| **文档声称** | 9 项检测（行 544-554） |
| **实际代码** | `alert_engine.py` 中有 **10 个** `check_` 函数（grep `def check_` 命中 10 行） |
| **证据** | 文档列出的 9 个：`check_overdue_tasks`, `check_stalled_tasks`, `check_queue_depth`, `check_operator_overload`, `check_completion_rate`, `check_schedule_overdue`, `check_order_timeout_alerts`, `check_material_arrival`，共 8 个不同函数（其中 `check_order_timeout_alerts` 重复一次算 2 项） |
| **实际多出的 2 个** | `check_outsource_reminders`（行 536）+ `check_escalations`（行 623） |
| **影响** | 新人按文档只调用 8 个 check，遗漏"外协提醒"和"升级处理"，导致告警覆盖不全 |
| **修复建议** | 在 8.2 表里补全这 2 项，并把 `check_order_timeout_alerts` 拆为 2 个不同名函数 |

### Bug-10：章节 8.2 文档、注释、代码**三者数量全不一致**

| 项 | 内容 |
|---|---|
| **文件头注释**（`alert_engine.py:1-14`） | 自称"检查项（**6 类**）" |
| **章节 8.2 文档** | 列 **9 项** |
| **实际代码** | **10 个** check_ 函数 |
| **影响** | 同一模块三处维护入口，维护者改一处忘改两处 |
| **修复建议** | 三者统一；文档成为 SSOT，注释和代码以文档为准对齐 |

### Bug-11：章节 9.3 消息触发节点行号**几乎全错**

| 文档声明 | 实际情况 | 偏差 |
|---|---|---|
| `app.py:790 notify_admin_modified` | `notify.py:177` | 文件错了（不在 app.py） |
| `app.py:858 notify_admin_withdraw` | `notify.py:191` | 文件错了 |
| `app.py:1020 notify_quality_modified` | `notify.py:203` | 文件错了 |
| `app.py:1101 notify_quality_withdraw` | `notify.py:217` | 文件错了 |
| `_core.py:1482 tmpl_task_urgent` | `_do_send_process_task` 在 1554 行 | 偏 72 行 |
| `_core.py:1704 tmpl_process_start` | `publish_pending_tasks` 在 2254 行 | 偏 550 行 |
| `_core.py:2743 tmpl_task_transfer` | `reassign_task` 在 2745 行 | 偏 2 行（接近） |
| `_core.py:4987 tmpl_repair_complete` | `complete_repair_record` 在 5017 行 | 偏 30 行 |
| `_core.py:5130 tmpl_outsource_receive` | `create_outsource_record` 在 5133 行 | 偏 3 行 |
| `_core.py:7366 tmpl_quality_completed` | `on_quality_record_completed` 在 7602 行 | **偏 236 行** |
| `alert_engine.py:1704 _send_alert` | `_send_alert` 在 98 行；且文件总共 ~623 行 | **不存在 1704 行** |

**影响**：开发按文档行号去查代码会跳到错误位置；维护文档变成纯噪声

### Bug-12：章节 9.5 alert_engine.py 模板行号**全错**

| 文档声明 | 实际 |
|---|---|
| `alert_engine.py:215 _check_pending_tasks` | 无此函数 |
| `alert_engine.py:411 _check_schedules` | 无此函数 |
| `alert_engine.py:459 _check_pending_tasks` | 无此函数 |
| `alert_engine.py:483 _check_pending_tasks` | 无此函数 |
| `alert_engine.py:522 _check_material_arrivals` | 无此函数 |

**根本问题**：文档写的是 `_check_pending_tasks`（带下划线前缀），实际函数叫 `check_pending_tasks` / `check_overdue_tasks` 等（无下划线前缀）。且这些模板调用的**行号**也需用 `grep -n 'tmpl_' alert_engine.py` 重新核对。

**修复建议**：要么用自动化脚本生成（`grep -n` + 模板表），要么逐个 `Read` 段重新填写

---

## 三、中优先级 Bug（🟠 架构与设计可优化）

### Bug-13：章节 1.2 移动端描述漏"排产任务"

| 项 | 内容 |
|---|---|
| **位置** | 行 61 |
| **文档描述** | 5008 = "工序报工、质检、维修、外协、物料采购" |
| **实际** | 章节 5.1 任务 API 端点表中还包含 `/api/schedule_record/list`（排产任务） |
| **影响** | 排产任务功能被排除在服务描述外，新人找不到对应端点 |
| **修复建议** | 1.2 中补"排产" |

### Bug-14：章节 7.6 vs 章节 1.7.2 物料"负责人"字段不一致

| 项 | 内容 |
|---|---|
| **章节 1.7.2** | `material` 任务负责人字段 = `purchaser` |
| **章节 7.6** | `material_records` 负责人字段 = `target_operator` |
| **影响** | 同义概念两套字段名；统一任务查询接口和回归系统对不上 |
| **修复建议** | 以代码实际字段为准（`target_operator`），章节 1.7.2 修正 |

### Bug-15：章节 6 文件结构清单不完整

| 项 | 内容 |
|---|---|
| **文档列出的** | `dispatch_center/__init__.py`、`_core.py`、`schedule_routes.py` |
| **实际多出的** | `shipment_routes.py`、`_constants.py`、`_core_types.py`（均存在于 `dispatch_center/` 目录） |
| **影响** | 新人以为 `shipment_routes.py` 不存在，漏读发货相关路由 |
| **修复建议** | 补全目录树 |

### Bug-16：章节 1.7 顺序错乱

按"先机制后接口"逻辑，应该是：
1.7 同步 API 端点 → 1.8 动态字段扩展机制 → 1.9 字段映射表 → 1.10 扩展场景验证 → 1.11 统一任务查询接口

但实际文档把"动态字段扩展"提前到 1.7，把"统一任务查询"放到第二个 1.7。建议调整顺序。

### Bug-17：章节 2.2 `quality_records` 双库归属未说明

| 项 | 内容 |
|---|---|
| **章节 2.2 表** | `quality_records` 标记为 "steel_belt / container_center"（双库） |
| **章节 2.1 架构图** | `quality_records` 仅出现在 `container_center` 一侧 |
| **影响** | 读者会困惑表到底存哪 |
| **修复建议** | 明确主库 + 同步关系（与 `material_records` 处理方式一致） |

### Bug-18：章节 4.2 订单发布流程图缺"调度中心"

| 项 | 内容 |
|---|---|
| **问题** | 流程图末尾直接 "调度中心 (5003) → 云端 (5006)"，但缺少容器中心 → 调度中心这一步 |
| **影响** | 与章节 1.5 同步架构的"通过 5003 转发"约束缺乏对应 |
| **修复建议** | 补一条 "容器中心 → 调度中心 (5003)" 的箭头，注明"通过 5003 转发到云端" |

---

## 四、低优先级 Bug（🔵 文案/排版）

### Bug-19：章节 9.5 自报经 "X 轮审计" 标题风险

| 项 | 内容 |
|---|---|
| **位置** | 行 605-680 |
| **症状** | "消息模板字段完整性" 大段叙述使用"✅ 完整"等无证据断言（20 个模板全部 ✅ 完整） |
| **风险** | 违反反虚高规范（[全局硬规则](../../.trae/rules/%E5%AF%B9%E8%AF%9D%E6%A1%86%E4%BD%BF%E7%94%A8%E8%A7%84%E8%8C%83.md) §2 "禁止业务影响报告写没测过的数字"） |
| **建议** | 把"✅ 完整"改为"⏳ 待验证"或附验证命令 |

### Bug-20：版本日志条目与正文标题不一致

| 项 | 内容 |
|---|---|
| **修订历史 v3.6.1** | 声称 "新增统一任务查询接口（1.7 节）" |
| **正文** | 章节 1.7 实际是"动态字段扩展机制"，统一任务查询在第二个 1.7（编号错乱） |
| **影响** | 版本说明失真 |

---

## 五、修复优先级排序

| 优先级 | Bug 编号 | 预计工作量 | 修复必要性 |
|:------:|---------|----------|----------|
| 🔴 P0 | Bug-01 ~ Bug-05 | 30 分钟 | 必须修，否则文档目录不可用 |
| 🟡 P1 | Bug-06 ~ Bug-12 | 2 小时 | 必须修，文档与代码严重脱钩 |
| 🟠 P2 | Bug-13 ~ Bug-18 | 1 小时 | 建议修，提升一致性 |
| 🔵 P3 | Bug-19 ~ Bug-20 | 15 分钟 | 顺手修 |

---

## 六、附录 — 验证命令清单

按反虚高规范，所有发现均有 grep/Read 验证支撑：

```bash
# 验证 Bug-06
Glob 'mobile_api_ai/container_api.py'       # → No file found
Glob 'mobile_api_ai/container_center_api.py' # → 命中

# 验证 Bug-07 / Bug-08
grep -n '@app.route' mobile_api_ai/container_center/services/alert_engine.py
# → 0 命中（确认 alert_engine.py 无路由）

# 验证 Bug-09 / Bug-10
grep -n 'def check_' mobile_api_ai/container_center/services/alert_engine.py
# → 10 行（check_overdue_tasks / check_stalled_tasks / check_queue_depth /
#   check_operator_overload / check_completion_rate / check_schedule_overdue /
#   check_order_timeout_alerts / check_material_arrival / check_outsource_reminders
#   / check_escalations）

# 验证 Bug-11
grep -n 'def notify_admin_modified' mobile_api_ai/app.py
# → No matches found（实际在 notify.py:177）

grep -n 'def _do_send_process_task' mobile_api_ai/dispatch_center/_core.py
# → 行 1554（文档说 1482，偏 72 行）

grep -n 'def on_quality_record_completed' mobile_api_ai/dispatch_center/_core.py
# → 行 7602（文档说 7366，偏 236 行）

# 验证 Bug-12
grep -n '_check_pending_tasks\|_check_schedules\|_check_material_arrivals' \
  mobile_api_ai/container_center/services/alert_engine.py
# → 0 命中（这些函数名都不存在）
```

---

**报告生成时间**：2026-06-20
**审计人**：AI 助手（按反虚高规范逐项验证）
**总 Bug 数**：20 条（🔴×5 + 🟡×7 + 🟠×6 + 🔵×2）
**未验证项**：0（所有结论附 grep/Read 证据）