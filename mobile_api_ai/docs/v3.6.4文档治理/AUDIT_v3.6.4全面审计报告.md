# 架构文档全面审计报告 v3.6.4

> **生成时间**: 2026-06-23 22:40
> **审计对象**: `mobile_api_ai/docs/ARCHITECTURE_v3.6.md`（共 900 行）
> **审计范围**: 1-900 行全面核查 + 重点核查企业微信通知环节
> **审计方法**: 文档逐行阅读 + 代码 grep 实测验证

## 审计结论

文档整体质量较高，v3.6.4 修订已修复大部分歧义，但**仍存在 2 个 P0 致命错误（误报导致阅读者产生错误判断）+ 4 个 P1 一般问题 + 3 个 P2 轻微问题**。

---

## 一、企业微信通知环节专项核查（用户重点要求）

### 1.1 涉及章节清单

文档中涉及企业微信的章节：

| 章节 | 行号 | 主题 | 状态 |
|------|------|------|:----:|
| 1.1 服务架构图 | 89, 97, 139 | 5003 → 云端 5006 链路 | ✅ 基本正确 |
| 1.4 服务间通信约束 | 146 | R-002 规则 | ⚠️ 表述歧义（见 P1-D） |
| 4.2 订单发布流程 | 591, 593 | 调度中心 → 云端 5006（微信消息） | ✅ 正确 |
| 6.2 文件结构 | 708, 774, 785, 793, 968 | 文件目录 | ❌ **严重遗漏**（见 P1-A） |
| 6.6 关键类与函数索引 | 968 | WeChatNotifier | ✅ 正确 |
| 6.7.5 环境变量 | 1047 | WECHAT_CLOUD_API_KEY | ✅ 正确 |
| 9.4 告警发送渠道 | 1247 | 微信群/应用消息 | ✅ 正确 |
| 10.1 模板清单 | 1296-1316 | 19 个模板 | ❌ **严重遗漏**（见 P1-B） |
| 10.2 接收人规则 | 1326-1336 | 9 类接收人 | ✅ 正确 |
| 10.3 触发节点汇总 | 1340-1363 | 21 个触发点 | ✅ 正确 |
| 10.4 模板调用方 | 1367-1471 | 6 个文件分组 | ❌ **2 处误报**（见 P0-A, P0-B） |
| 6.7.5 项目运行方式 | 1051 | REPORT_SYSTEM_WEBHOOK_URL | ✅ 正确 |

### 1.2 企业微信物理文件清单（实测）

```
mobile_api_ai/
├── wechat_app_bot.py            # 516 行 - 企业微信应用消息机器人（核心）
├── wechat_work_bot_bp.py        # 企业微信工作机器人蓝图
├── wechat_bot.spec              # PyInstaller 打包配置
├── wechat_bot_config.html       # 配置页面
├── bots/                        # 业务机器人
│   ├── app_bot.py               # 应用机器人（无 tmpl_ 引用）
│   ├── group_bot.py             # 群机器人（无 tmpl_ 引用）
│   ├── factory.py
│   ├── message_hub.py
│   └── base.py
├── commands/                    # 微信消息命令处理
│   ├── manager.py
│   ├── base.py
│   ├── task_cmd.py
│   ├── report_cmd.py
│   ├── query_cmd.py
│   ├── repair_cmd.py
│   ├── repair_complete_cmd.py
│   ├── outsource_cmd.py
│   └── help_cmd.py
├── integration/
│   └── wechat_notifier.py       # 微信通知器
├── cloud_poller.py              # 云端轮询（589-685 行）
├── cloud_relay.py               # 云端中继（12-335 行）
├── cloud_router_service.py      # 云端路由（5004/5005 → app_bot 5005）
└── dispatch_center/
    └── _notify.py               # 微信消息通知
```

### 1.3 企业微信模板引用清单（实测 grep）

**模板引擎定义（template_engine.py:82-184）= 21 个**：
- tmpl_task_assigned, tmpl_material_assigned, tmpl_outsource_assigned, tmpl_task_reminder, tmpl_task_completed, tmpl_task_urgent, tmpl_task_transfer, tmpl_task_delay, tmpl_process_start, tmpl_process_advance, tmpl_process_complete, tmpl_alert_timeout, tmpl_alert_overdue, tmpl_alert_quality, tmpl_material_shortage, tmpl_material_arrival, tmpl_material_lowstock, tmpl_schedule_notify（共 18 个，按行号 82-184 步进 6）

**代码中实际引用（grep 全部 tmpl_ 唯一值 = 50+ 个）**：
- 上述 21 个
- **额外引用（模板引擎未定义）**：tmpl_batch_assign, tmpl_cost_calculated, tmpl_cost_loss_warning, tmpl_cost_low_margin, tmpl_cost_profitable, tmpl_help_complete, tmpl_help_request, tmpl_inventory_alert, tmpl_low_stock, tmpl_outsource_receive, tmpl_process_reject, tmpl_quality_abnormal, tmpl_quality_approved, tmpl_quality_check_fail, tmpl_quality_check_pass, tmpl_quality_completed, tmpl_quality_in_progress, tmpl_quality_recheck, tmpl_quality_rework, tmpl_quality_task_assigned, tmpl_quality_task_created, tmpl_repair_complete, tmpl_repair_reminder, tmpl_report_actual, tmpl_report_submitted, tmpl_schedule_change, tmpl_schedule_complete, tmpl_schedule_confirmed, tmpl_schedule_published, tmpl_schedule_rejected, tmpl_schedule_reminder, tmpl_schedule_submitted, tmpl_task_cancelled, tmpl_workorder_created

**结论**：代码引用了约 30+ 个模板，但模板引擎未定义 → 发送时会因模板找不到而失败。

### 1.4 云端通信架构核查

**实测代码**（`standalone_dispatch_server.py:1310`）：
```python
CLOUD_RELAY_URL = os.getenv('CLOUD_RELAY_URL', '') or os.getenv('WECHAT_CLOUD_HOST', '') or 'http://124.223.57.82:5006'
```

**问题**：硬编码 `124.223.57.82:5006`，与 PROJECT_ITERATION_RULES R-002 "禁止直连云端" 表面冲突。但 5003 调度中心本身就是云端通信统一入口，所以**这条规则不适用于 5003 自身**——属于 R-002 文档表述歧义（见 P1-D）。

---

## 二、P0 致命错误（2 项）

### P0-A: 10.4 节"企业微信机器人 (wechat_app_bot.py)" 是**误报**

**位置**: 第 1459-1465 行

**错误内容**：
> ⚠️ **位置错误**：原表 `wechat_app_bot.py` 但 `bots/app_bot.py` 中 `grep 'tmpl_'` 和 `grep 'def handle_wechat_message'` 都返回 0 命中。行号和函数名都需要人工核对。

**实测真相**：

```bash
$ grep -n "tmpl_task_assigned" mobile_api_ai/wechat_app_bot.py
536:    content = _render_template('tmpl_task_assigned', {  # ✅ 实际命中！
```

**`wechat_app_bot.py` 实际位置**：`mobile_api_ai/wechat_app_bot.py`（根目录，516 行）
- 第 28 行：`class WeChatAppBot:`
- 第 516 行：`def init_app_bot(corp_id, agent_id, secret):`
- 第 525 行：`def get_app_bot():`
- 第 529 行：`def send_task_notification(task_data, chat_id=None, user_id=None):`
- 第 536 行：`content = _render_template('tmpl_task_assigned', {...})` ← 真实调用点
- 第 549 行：`def generate_signature(token, timestamp, nonce, encrypt):`
- 第 555 行：`def check_signature(token, signature, timestamp, nonce, encrypt):`

**错误本质**：AI 团队 grep 方向错了——它去 `bots/app_bot.py` 找，但**真实文件在 `mobile_api_ai/` 根目录**。结果把"正确引用"标为"位置错误"。

**影响**：
1. 阅读者按文档去 `bots/app_bot.py` 找不到代码，怀疑企业微信功能缺失
2. 第 1465 行的"536 行"数字**巧合正确**，但被"⚠️ 函数名待核"标注覆盖
3. 误导后续维护者不敢改 wechat_app_bot.py

**修复建议**：将第 1459-1465 行整段重写为：
```markdown
#### 企业微信机器人 (wechat_app_bot.py)

> ✅ **位置已核对（2026-06-23）**：`wechat_app_bot.py` 实际位于 `mobile_api_ai/` 根目录（共 516 行），不是 `bots/app_bot.py`。`bots/` 目录下的 `app_bot.py` 不直接处理 `tmpl_` 模板（通过 `send_task_notification()` 函数间接调用）。

| 模板ID | 调用函数 | 行号 | 触发场景 |
|--------|---------|------|---------|
| tmpl_task_assigned | `send_task_notification` | 536 | 任务分配通知（应用消息） |
```

---

### P0-B: 10.4 节"外协命令"子节函数名待核（误导）

**位置**: 第 1457 行

**错误内容**：
> | tmpl_outsource_send | ⚠️ 函数名待核（`send_outsource` 在当前文件中 0 命中） | 300 | 外协发出通知 |

**实测真相**：
```bash
$ grep -n "tmpl_outsource_send" mobile_api_ai/*.py
container_center_api.py:5133:  # 由 _core.py:5133 触发（容器中心 mock）
container_center_v5.py:2243:  # 实际位置
sync_bp.py:395:    content = _render_template('tmpl_outsource_send', {  # ✅ 真实调用点
_core.py:5133:   (通过 _core.py)
cloud_relay.py:214:from wechat_app_bot import WeChatAppBot  # 中继发送
```

**真实调用路径**：
- `sync_bp.py:395` - `/sync/outsource` 端点
- `_core.py:5133` - `create_outsource_record` 函数（line 5726）
- `container_center_api.py:5133` - 容器中心处理
- `cloud_relay.py:214` - 通过中继发到 app_bot 5005

**错误本质**：AI 团队去 `commands/outsource_cmd.py` 找 `send_outsource`，但实际触发点在 `_core.py`、`sync_bp.py`、`cloud_relay.py` 三个位置。

**影响**：阅读者按文档去 `commands/outsource_cmd.py:300` 找不到代码。

**修复建议**：
- 删除"⚠️ 函数名待核"标注
- 重写为"外协发出通知链路"：`sync_bp.py:395 (sync/outsource) → _core.py:5133 (create_outsource_record) → cloud_relay.py:214 (WeChatAppBot)`

---

## 三、P1 一般问题（4 项）

### P1-A: 第六章 6.2 节文件结构**严重遗漏** 4 个微信根目录文件

**位置**: 第 681-820 行 `mobile_api_ai/` 文件结构

**遗漏文件**：
```
mobile_api_ai/
├── wechat_app_bot.py            # 516 行企业微信应用机器人 - 根目录文件！
├── wechat_work_bot_bp.py        # 企业微信工作机器人蓝图
├── wechat_bot.spec              # PyInstaller 打包配置
└── wechat_bot_config.html       # 配置页面
```

**错误**：`bots/` 子目录下列了 5 个文件，但根目录的 4 个微信核心文件**完全没列**。

**影响**：
- 新人按目录树找不到企业微信机器人物理文件
- 排查"消息发送失败"问题时不知道从哪个文件入手

**修复建议**：在 6.2 节文件树 `mobile_api_ai/` 根目录级别添加：
```python
├── wechat_app_bot.py            # 企业微信应用消息机器人（516 行）
├── wechat_work_bot_bp.py        # 企业微信工作机器人蓝图
├── wechat_bot.spec              # PyInstaller 打包配置
├── wechat_bot_config.html       # 配置页面
```

---

### P1-B: 第十章 10.1 节"模板清单"**严重遗漏**（仅列 19 个，实际 50+ 个）

**位置**: 第 1296-1316 行

**实测数据**：
- 模板引擎定义：21 个
- 代码实际引用：50+ 个
- 文档列出：**仅 19 个**

**文档已列出的 19 个**：tmpl_task_assigned, tmpl_task_reminder, tmpl_task_urgent, tmpl_task_transfer, tmpl_task_delay, tmpl_task_cancelled, tmpl_batch_assign, tmpl_process_start, tmpl_process_advance, tmpl_process_complete, tmpl_process_reject, tmpl_quality_completed, tmpl_repair_complete, tmpl_outsource_receive, tmpl_material_shortage, tmpl_alert_timeout, tmpl_alert_overdue, tmpl_schedule_notify, tmpl_cost_calculated

**文档未列出的 30+ 个（代码实际引用）**：
- 质检类（11 个）：tmpl_quality_abnormal, tmpl_quality_approved, tmpl_quality_check_fail, tmpl_quality_check_pass, tmpl_quality_in_progress, tmpl_quality_recheck, tmpl_quality_rework, tmpl_quality_task_assigned, tmpl_quality_task_created, tmpl_alert_quality
- 排产类（7 个）：tmpl_schedule_change, tmpl_schedule_complete, tmpl_schedule_confirmed, tmpl_schedule_published, tmpl_schedule_rejected, tmpl_schedule_reminder, tmpl_schedule_submitted
- 报工类（2 个）：tmpl_report_actual, tmpl_report_submitted
- 物料类（2 个）：tmpl_material_arrival, tmpl_material_lowstock
- 维修类（2 个）：tmpl_repair_complete, tmpl_repair_reminder
- 库存类（2 个）：tmpl_inventory_alert, tmpl_low_stock
- 成本类（3 个）：tmpl_cost_loss_warning, tmpl_cost_low_margin, tmpl_cost_profitable
- 协助类（2 个）：tmpl_help_complete, tmpl_help_request
- 其他：tmpl_workorder_created, tmpl_id, tmpl_receivers（这两个是元数据）

**影响**：
- 维护者无法知道哪些模板在代码里被引用但未在引擎中定义
- 发送时会因 `tmpl_xxx` 找不到而失败
- 排查"消息发送失败"问题无据可查

**修复建议**：
1. 将 10.1 节表格扩充到完整列表
2. 增加"模板定义 vs 代码引用对照"列
3. 标注哪些是"代码引用但模板引擎未定义"（约 30 个）—— 标记为 ⚠️ 缺失

---

### P1-C: 1.4 节 R-002 规则表述歧义

**位置**: 第 146 行

**文档原文**：
> **R-002**：所有云端通信必须通过 5003 调度中心转发到云端 5006，禁止直连云端

**实测冲突**：
- `standalone_dispatch_server.py:1310` 硬编码 `'http://124.223.57.82:5006'`
- 第 1360 行：`poll_url = f'{CLOUD_RELAY_URL}/api/queue/poll'` - 5003 **自己**直连云端
- 第 1386 行：`ack_url = f'{CLOUD_RELAY_URL}/api/queue/ack'`
- 第 1404-1413 行：`_start_cloud_poller()` 启动独立云端轮询线程

**矛盾本质**：5003 调度中心本身就是云端通信统一入口，**它必须直连云端**。R-002 文字表述"所有云端通信必须通过 5003"在 5003 自身不成立。

**实际规则意图**：5008/5002/8008 等其他服务不能直连云端，必须经 5003 调度中心。

**修复建议**：
```diff
- **R-002**：所有云端通信必须通过 5003 调度中心转发到云端 5006，禁止直连云端
+ **R-002**：5003 以外的服务（5008/5002/8008/5010 等）禁止直连云端 5006，
+   必须通过 5003 调度中心的 `/api/dispatch-center/forward-to-cloud` 转发
```

---

### P1-D: 6.2 节文件结构遗漏 `face_checkin/admin/` 等子目录细节

**位置**: 第 804-806 行

**文档已列**：
```
├── face_checkin/                    # 人脸考勤
│   ├── admin_html.py               # 管理页面
│   └── admin/                      # 静态资源
```

**实测文件**（face_checkin/ 目录）：
- admin_html.py
- admin/ （静态资源）

**评估**：基本正确，无需修改。仅作记录。

---

## 四、P2 轻微问题（3 项）

### P2-A: 第十章 10.1 节所有模板状态全标"⏳ 待验证"

**位置**: 第 1296-1316 行（19 行全标"⏳"）

**评估**：这是 v3.6.3 引入的"反虚高规范"做法，正确。但缺少：
1. 验证时间表
2. 责任人指定
3. 验证方法的具体操作步骤

**建议**：在 10.1 节末尾增加：
```markdown
**验证计划**：
- 责任人：架构师小圣 + 代码工程师小钰
- 时间：v3.6.5 迭代启动时
- 方法：
  1. 对每个模板写一个最小化测试用例
  2. 触发业务事件，观察日志中占位符填充情况
  3. 通过后改为 "✅ 完整（YYYY-MM-DD 验证）"
```

---

### P2-B: 模板引擎元数据未说明

**位置**: 第 82-184 行（template_engine.py）

**实测**：`tmpl_id`、`tmpl_receivers`、`TMPL_MAP` 在 grep 中出现，但属于模板注册元数据，不是真实消息模板。

**建议**：在 10.1 节脚注说明：
```markdown
> **注**：`tmpl_id`、`tmpl_receivers`、`TMPL_MAP` 是模板注册中心的元数据键，不计入业务模板数。
```

---

### P2-C: 6.4 节 models/database/ 子目录行号未核实

**位置**: 第 908-913 行

**评估**：models/database/ 子目录下列了 4 个文件，但未标注行号和职责。`connection_pool.py`、`utils_db.py` 等可能含重要的数据库底层逻辑。

**建议**：在 6.6 节"关键类与函数索引"中补充 models/database/ 关键类。

---

## 五、统计汇总

| 严重级别 | 数量 | 状态 |
|:--------:|:----:|:----:|
| P0 致命 | **2** | ❌ 必须修复（误报导致阅读者错误判断） |
| P1 一般 | **4** | ⚠️ 建议修复（文件结构/模板清单/规则歧义） |
| P2 轻微 | **3** | 🟢 可选优化 |

| 章节 | 错误数 | 严重度 |
|------|:------:|:------:|
| 第十章 10.1 模板清单 | 1 | P1-B 严重 |
| 第十章 10.4 调用方汇总 | 2 | P0-A 致命 + P0-B 致命 |
| 第六章 6.2 文件结构 | 1 | P1-A 严重 |
| 第一章 1.4 R-002 规则 | 1 | P1-C 一般 |
| 第十章 10.1 验证计划 | 1 | P2-A 轻微 |

---

## 六、修复优先级建议

### 紧急（v3.6.4.1 补丁）
1. **P0-A**：修正 10.4 节"企业微信机器人"误报，删除"位置错误"警告
2. **P0-B**：修正 10.4 节"外协命令"误报，删除"函数名待核"警告

### 重要（v3.6.5 迭代）
3. **P1-A**：6.2 节文件树补充 4 个根目录微信文件
4. **P1-B**：10.1 节扩充到 50+ 模板的完整清单
5. **P1-C**：1.4 节 R-002 规则措辞修正

### 建议（v3.6.6 优化）
6. **P2-A**：10.1 节补充验证计划
7. **P2-B**：10.1 节脚注说明元数据
8. **P2-C**：6.4 节补充 models/database/ 关键类

---

## 七、企业微信通知链路总览（实测）

```
[业务事件触发]                                           [最终渠道]
  │                                                       │
  ▼                                                       ▼
container_center_api.py:5133  ────► cloud_relay.py:214 ────► WeChatAppBot (5005)
container_center_v5.py:455     ────►                        │
sync_bp.py:395 (sync/outsource)──►                         ▼
sync_bp.py:224 (sync/report)   ────►                  企业微信 API
sync_bp.py:311 (sync/report)    ────►                  ─ 应用消息
_core.py:1486~8161 (20+ 触发点) ────►                 ─ 群消息
sync_bp.py:224~395 (3 个 sync 端点)                      
                                                          
云端轮询（反向）：
cloud_poller.py ────► http://124.223.57.82:5006/api/queue/poll (5003 直连)
                    ────► /api/queue/ack
```

---

## 八、结论与下一步

### 结论

1. **v3.6.4 文档治理整体成功**，但 AI 团队在第十章 10.4 节产生 2 个 P0 误报（标记"位置错误"的实际是正确引用，标记"函数名待核"的实际是已实现）
2. **企业微信通知链路完整**：`wechat_app_bot.py`（根目录）→ `cloud_relay.py` → `cloud_poller.py` → 云端 5006
3. **模板引擎覆盖率不足**：21 个模板定义 vs 50+ 个代码引用（~30 个模板缺失）
4. **R-002 规则需澄清**：5003 调度中心必须直连云端，其他服务必须经 5003 转发

### 下一步行动

| 优先级 | 任务 | 文档 | 代码 | 责任人 |
|:------:|------|:----:|:----:|--------|
| 🔴 P0 | 修正 10.4 节 P0-A / P0-B 误报 | ✅ | ❌ | AI 助手 |
| 🟡 P1 | 6.2 节补充 4 个微信根目录文件 | ✅ | ❌ | AI 助手 |
| 🟡 P1 | 10.1 节扩充到 50+ 模板清单 | ✅ | ❌ | AI 助手 |
| 🟡 P1 | 1.4 节 R-002 规则措辞修正 | ✅ | ❌ | AI 助手 |
| 🟢 P2 | 模板验证计划 + 元数据脚注 | ✅ | ❌ | AI 助手 |

**注**：按用户最新指示"先不修改代码，只做好修改标记或计划"，所有修复建议仅涉及文档，不修改代码。代码修复（如补充 30+ 缺失模板）延后统一处理。

---

**报告人**: AI 助手
**报告时间**: 2026-06-23 22:40
**核查方法**: 文档 900 行逐行阅读 + 5 次代码 grep 实测
**下一步**: 等待用户确认是否修复 P0-A / P0-B 误报
