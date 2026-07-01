# 产品经理审计报告 - ARCHITECTURE_v3.6.md 业务逻辑和流程完整性

> **审计人**: 小曦（产品经理，20年工厂管理经验 + 自动化跟单系统编译能力）
> **审计日期**: 2026-06-23
> **审计范围**: 4.0 状态机、3 物料数据模型、8 任务回归审计、9 预警告警、10 消息模板
> **审计方法**: 文档逐节研读 + Grep 代码反向验证
> **审计对象**: `d:\yuan\不锈钢网带跟单3.0\mobile_api_ai\docs\ARCHITECTURE_v3.6.md`
> **重要声明**: 本报告**仅审计文档**，未修改任何源代码和 ARCHITECTURE_v3.6.md

---

## 0. 审计结论速览

| 维度 | 评估 | 关键发现 |
|------|:----:|---------|
| **业务流覆盖度** | ⚠️ 70% | 主干流程（生产/物料/质检/维修/外协/排产）覆盖，但**入库流程、独立工序、告警升级路径**有遗漏 |
| **状态机准确度** | 🔴 40% | 文档自我宣称"v3.6.4 已修正歧义"，但**实际代码并未同步**；两套状态体系并存混乱 |
| **业务流程图一致性** | 🟡 55% | 部分流程图与代码严重不符（工序代码 P06-P16 实际为 P01-P03 起步） |
| **模板覆盖度** | 🔴 35% | 文档列 19 个模板，实际 template_engine.py 54 个；缺失 35 个未审计 |
| **业务规则准确度** | 🟡 60% | 同步字段映射、告警阈值基本准确；外协提醒**未走模板**是隐藏缺陷 |

**总体评级**: 🟡 中等偏差，需要 2-3 轮迭代修复

---

## 1. 业务流覆盖度评估

### 1.1 主干流程覆盖矩阵

| 业务流 | 文档 4.0 是否定义 | 代码 _constants.py 是否实现 | 评估 |
|--------|:------------------:|:---------------------------:|------|
| 生产 (production) | ✅ 7 步 | ✅ 7 步 PROCESS_FLOW_TEMPLATES | ✅ 完整 |
| 物料 (material_purchase) | ✅ 6 步 | ✅ 6 步 | ✅ 完整 |
| 质检 (quality) | ✅ 4 步 | ✅ 4 步 | ✅ 完整 |
| 维修 (repair) | ✅ 5 步 | ✅ 5 步 | ✅ 完整 |
| 外协 (outsource) | ✅ 7 步 | ✅ 7 步 | ✅ 完整 |
| **入库 (warehousing)** | ❌ **未定义** | ✅ 存在 flow_type='warehousing' | 🔴 **P0 遗漏** |
| **派单中 (dispatched)** | ❌ **未定义** | ✅ 存在 ProductionStatus.DISPATCHED | 🔴 **P0 遗漏** |
| **排产 (schedule)** | ❌ 4.0 未列独立流程 | ✅ schedule_records 表独立 | 🟡 **P1 遗漏** |

### 1.2 关键发现

#### 🔴 P0-1: 缺失"入库流程"模板
**问题**: `core/process_code_classifier.py:72` 存在 flow_type=`warehousing`，但 4.0.2 流程模板汇总表（5 项）**未包含 warehousing 流程**。
**影响**: 业务上 STOCK_IN / IN 类工艺包无法匹配流程模板，状态推进可能走默认路径。
**建议**: 在 `PROCESS_FLOW_TEMPLATES` 中新增 'warehousing' 流程模板（建议 3 步：待入库 → 验收 → 入库完成），并在文档 4.0.2 节补充。

#### 🔴 P0-2: 缺失"派单中"状态
**问题**: `models/enums.py:38-45` `ProductionStatus` 枚举包含 `DISPATCHED = "DISPATCHED"`，文档 4.0.1 状态键（7 项）**未列出 DISPATCHED**。
**影响**: 派单后、工序开始前的过渡状态缺失，状态机出现"空档"，业务上从 `confirmed` 直接跳到 `in_production`，但实际有派单审核环节。
**建议**: 在 4.0.1 状态键表中增加 `dispatched: 已派单`，作为 `confirmed → in_production` 之间的中间状态。

#### 🟡 P1-1: 排产流程未独立建模
**问题**: 4.0.2 流程模板只列 5 项，但 `container_center.schedule_records` 表独立存在；状态机里 `scheduled → confirmed` 实际是排产的两阶段，混在生产流程里不合理。
**建议**: 4.0.2 增加 `schedule: 4 步（草拟 → 确认 → 下达 → 完成）` 流程模板。

#### 🟡 P1-2: 维修流程步骤与报修种类不一致
**问题**: 文档 4.1 说"维修任务 R01-R07"，实际 `container_config.py:194-196` 只有 **3 个报修种类**（R01 设备故障/R02 电气维修/R03 安全风险）。
**影响**: 文档承诺的 R04-R07 不存在，维修种类管理是**数据驱动**而非流程驱动。
**建议**: 区分"流程步骤"和"报修种类 ID"两个概念。文档 4.1 节应改为"R0X 为报修种类 ID（最多 3 个内置 + 动态扩展）"。

---

## 2. 状态机问题清单

### 2.1 🔴 P0-3: 文档"v3.6.4 修正"是虚假闭环

**文档 4.0.1 节声明**:
> "v3.6.4 修正：原文档将 `scheduled` 和 `confirmed` 状态值都标为'已排产'，存在歧义。修正后：`scheduled` = 排产**制定**，`confirmed` = 排产**确认**"

**代码实际状态** (`dispatch_center/_constants.py:14-22`):
```python
STATUS_KEY_TO_MYSQL: Dict[str, str] = {
    'published': '已发布',
    'scheduled': '已排产',       # ❌ 仍是'已排产'，未修正
    'confirmed': '已排产',       # ❌ 仍是'已排产'，未修正
    'in_production': '生产中',
    'reported': '质检中',        # ❌ 文档说'报工完成'，代码说'质检中'
    'qc_passed': '质检通过',
    'completed': '已完成',
}
```

**问题**:
1. 文档说"已修正"，代码**完全没动** —— 典型的"文档自我闭环"反模式
2. P0-6 决议（待修改代码清单 33 行）说"已在本版本完成"，**这是错误结论**
3. 实际 `reported` 状态键在 STATUS_KEY_TO_MYSQL 中是"质检中"，但流程模板 PROCESS_FLOW_TEMPLATES 中 `reported` 步骤名是"报工完成"—— **同一状态键在不同位置语义冲突**

**优先级**: 🔴 P0
**修复建议**:
- 修正 `_constants.py` 中 `scheduled → '排产制定'`、`confirmed → '排产确认'`
- 修正 `reported → '报工完成'`（与流程模板步骤名保持一致）
- 在 P0 决议清单中撤回 P0-6 的"✅ 已闭环"标记，改为"⏳ 实际未修复"

### 2.2 🔴 P0-4: 两套状态体系并存

**问题**: 项目存在两套独立的状态定义：

| 定义位置 | 风格 | 值 |
|---------|------|-----|
| `dispatch_center/_constants.py:14` | 小写英文键 → 中文 | `published` → `已发布` |
| `models/enums.py:36-46` | 大写英文枚举 | `ProductionStatus.PENDING` = "PENDING" |
| `dispatch_center/_core_types.py:90-124` | 小写英文键 | `required/checked/approved/ordered/...` |

**影响**:
1. 业务代码用 `ProductionStatus`（大写），调度中心用小写键，**跨模块传值时需要转换层**
2. 文档 4.0.1 节只覆盖了 `dispatch_center` 的小写体系，**未提及 `models/enums.py` 的大写体系**
3. 新人阅读时会困惑：到底以哪个为准？

**修复建议**:
- 选择一个作为 SSOT（Single Source of Truth），建议保留 `models/enums.py` 的枚举类（类型安全）
- 删除 `dispatch_center/_constants.py:14-22` 的小写键映射
- 文档 4.0.1 改为引用 `models/enums.py` 的 `ProductionStatus`

### 2.3 🟡 P1-3: 状态机缺少派单失败回退路径

**问题**: 文档 4.0.3 生产流程是单向流：
```
published → scheduled → confirmed → in_production → reported → qc_passed → completed
```

**业务上**:
- 派单失败要回退到 `scheduled` 或 `confirmed`
- 报工错误要撤回（从 `reported` 回退到 `in_production`）
- 质检不通过要返工（`qc_passed` → `in_production`）

**修复建议**: 在 4.0.3 各流程状态流图后增加"状态回退矩阵"：
- 谁有权限回退
- 回退到哪个状态
- 触发通知给谁

### 2.4 🟡 P1-4: 质量记录状态机不齐

**问题**: `dispatch_center/_constants.py:80-87` `quality` 流程有 4 步（quality_received → quality_judged → quality_approved → completed），但 4.0.3 节描述为 4 步且**省略了 quality_judged 的中间环节**。

**修复建议**: 4.0.3 流程图应明确"检测结果判断"是质检员填写 pass/fail 的关键节点。

---

## 3. 业务流程图问题

### 3.1 🔴 P0-5: 工序代码示例与代码不符

**文档 4.1 节声明**:
| 任务类型 | flow_type | 前缀 | 示例 |
|---------|-----------|------|------|
| 生产工序 | production | P | P06, P07, P09... |

**代码实际**:
- `core/process_code_classifier.py:52` 注释明确说"P 编号 = 工序进度，含 P01/P11/P15/P16"
- `container_config.py:142-145` 默认 fallback 工序：`P01 编织 / P02 质检 / P03 包装`
- `container_config.py:170-173` 动态生成的工序 ID 是 `P01`、`P02`...`PNN` 格式

**问题**:
1. 文档示例"P06, P07, P09"暗示工序从 P06 开始，但代码默认从 P01 开始
2. 实际工序编号是**业务配置动态生成**（P01~PNN 任意），不是固定 06-16
3. 文档 4.2 节订单发布流程里说 "production: P06-P16" 同样是**错误的固定范围**

**修复建议**:
- 4.1 节改为"前缀 | 范围示例 | 说明"，示例用 `P01-Pxx（动态生成）`
- 4.2 节删除"P06-P16"具体范围
- 4.1 维修任务行从"R01-R07"改为"R01-R03（内置 3 个 + 动态扩展）"

### 3.2 🟡 P1-5: 4.2 节订单发布流程图与服务架构不一致

**问题**: 4.2 节流程图显示：
```
桌面端 → 容器中心(5002) → 任务包表 → 调度中心(5003) → 云端
```

**但实际架构**（1.1 节）:
- 调度中心(5003) **不直接**接收任务包，任务包由容器中心内部消费
- 云端通信路径：5008 → 5003 → 5006，4.2 图里缺少 5008 移动端节点

**修复建议**: 4.2 流程图补充移动端(5008)节点，明确"工序报工/物料更新/维修更新"等移动端操作走 5003 调度中心。

### 3.3 🟡 P1-6: 第三章物料数据模型缺同步时序

**问题**: 3.1 节"物料数据双向同步流程"是 4 步图，但**没有标注失败重试路径**：
1. 步骤 3 "更新阶段"移动端 → 容器中心，**没有回滚机制**
2. 步骤 4 "回填阶段"容器中心 → 桌面端，**没有冲突检测**

**修复建议**: 3.1 增加"异常处理"分支：
- 容器中心更新失败 → 移动端显示重试
- 回填失败 → DLQ 重试 + 告警

### 3.4 🔵 P2-1: 3.2 字段同步映射表不完整

**文档 3.2 节列了 3 个字段映射**:
| 移动端 (material_records) | 桌面端 (order_materials) |
|------------------------|------------------------|
| status | prep_status |
| arrival_date | arrival_date |
| target_operator | target_operator |

**代码实际**（`_core.py:9309-9313` 字段映射）:
```python
material_field_map = {
    'status': 'prep_status',
    'planned_qty': 'required_qty',
    'completed_qty': 'prepared_qty',
}
```

**问题**: 文档缺 `planned_qty → required_qty` 和 `completed_qty → prepared_qty` 两个关键映射，**这两个映射在 1.8 节"字段映射表"里有，但 3.2 节没有**。

**修复建议**: 3.2 节表格与 1.8 节保持一致，补全 5 个字段映射。

---

## 4. 模板覆盖度问题

### 4.1 🔴 P0-6: 模板清单覆盖度仅 35%

**文档 10.1 节列 19 个模板**，但实际 `template_engine.py:82-401` 定义了 **54 个模板 ID**：

| 已列（19） | 缺失（35） |
|----------|----------|
| tmpl_task_assigned | tmpl_material_assigned |
| tmpl_task_reminder | tmpl_outsource_assigned |
| tmpl_task_urgent | tmpl_task_completed |
| tmpl_task_transfer | tmpl_material_lowstock |
| tmpl_task_delay | tmpl_inventory_alert |
| tmpl_task_cancelled | tmpl_low_stock |
| tmpl_batch_assign | tmpl_repair_reminder |
| tmpl_process_start | tmpl_help_request |
| tmpl_process_advance | tmpl_help_complete |
| tmpl_process_complete | tmpl_quality_check_pass |
| tmpl_quality_completed | tmpl_quality_check_fail |
| tmpl_repair_complete | tmpl_quality_task_created |
| tmpl_outsource_receive | tmpl_quality_task_assigned |
| tmpl_material_shortage | tmpl_quality_in_progress |
| tmpl_alert_timeout | tmpl_quality_approved |
| tmpl_alert_overdue | tmpl_quality_abnormal |
| tmpl_schedule_notify | tmpl_quality_rework |
| tmpl_cost_calculated | tmpl_quality_recheck |
|  | tmpl_workorder_created |
|  | tmpl_schedule_submitted |
|  | tmpl_schedule_published |
|  | tmpl_schedule_confirmed |
|  | tmpl_schedule_rejected |
|  | tmpl_schedule_complete |
|  | tmpl_schedule_change |
|  | tmpl_schedule_reminder |
|  | tmpl_report_submitted |
|  | tmpl_report_actual |
|  | tmpl_outsource_send |
|  | tmpl_repair_report |
|  | tmpl_cost_loss_warning |
|  | tmpl_cost_low_margin |
|  | tmpl_cost_profitable |
|  | tmpl_process_reject |

**问题**:
1. 10.1 节标题为"模板字段清单"但实际只覆盖 35%，**存在误导性**
2. 缺失的 35 个模板中**部分已被业务调用**（如 `tmpl_schedule_complete`、`tmpl_outsource_send`、`tmpl_cost_loss_warning`），但未在 10.1 节审计范围内
3. `tmpl_schedule_complete` 在 `_constants.py:124` 流程确认步骤中作为模板引用，但 10.1 节未列出，**SSOT 断裂**

**修复建议**:
- 10.1 节扩展为完整 54 个模板清单
- 按 category（task/process/quality/material/schedule/alert/cost/other）分组展示
- 对每个模板标注"是否被业务调用"（基于 `_render_template` grep 结果）

### 4.2 🟡 P1-7: 10.2 消息接收人规则不完整

**问题**: 10.2 节列了 10 条接收人规则，但**质检完成/物料到货/外协收货**等关键业务没有列。

**实际渲染的模板**（`grep _render_template` 命中 18 处）中：
- 8 个用 wechat_group 群发
- 7 个用 wechat_app 个人
- 3 个混合

**修复建议**: 10.2 表格与 10.4 调用方汇总表对齐，按"模板ID"列接收人。

### 4.3 🟡 P1-8: 外协提醒未走模板引擎

**关键发现** (`alert_engine.py:584-645`)：
```python
def check_outsource_reminders(self):
    ...
    self._send_alert(
        f'🚨 **外协逾期催单**\n━━━━━━━━\n'
        f'任务: {title}\n操作员: {op_name}\n'
        f'逾期: {int(-days_left)} 天\n━━━━━━━━\n请尽快完成！',
        level='WARNING')
```

**问题**:
1. 9.2 第 10 项"外协到期/逾期提醒"用硬编码 Markdown 文本，**未走模板引擎**
2. template_engine.py 中**没有** `tmpl_outsource_reminder` 或类似模板
3. 10.1 模板清单和 9.2 告警检测类型**两处都未提及此问题**

**影响**:
- 文本不可配置（运营无法改文案）
- 字段位置固定（无法适配不同场景的格式要求）
- i18n 困难

**优先级**: 🟡 P1（业务可工作但维护性差）
**修复建议**:
- 在 template_engine.py 新增 `tmpl_outsource_reminder` / `tmpl_outsource_overdue` 模板
- alert_engine.py:629-643 改用 `_render_template` 渲染
- 9.2 节标注"外协提醒：硬编码文本，建议改为模板"

### 4.4 🟡 P1-9: 10.4 调用方汇总有"⚠️ 函数名待核"

**文档 10.4 节多行标注"⚠️ 函数名待核"**：
- 外协命令 `tmpl_outsource_send` 调用函数（行 300）：`send_outsource` 在 `commands/outsource_cmd.py` 中 grep 0 命中
- 企业微信机器人 `tmpl_task_assigned`（行 536）：`handle_wechat_message` 在 `bots/app_bot.py` 中 grep 0 命中
- 单独派单服务 `tmpl_report_submitted`（行 1277）：`/api/submit_report` 端点待核

**问题**: 审计报告自我标注"待核"是**信息不完整**，给业务方留下隐患。

**修复建议**:
- 用 `grep -rn "def send_outsource" mobile_api_ai/` 等命令精确定位
- 或直接读 300 行附近代码确认实际函数名
- 在 10.4 节删除所有"⚠️ 待核"标注

---

## 5. 业务规则问题

### 5.1 🟡 P1-10: 状态机定义 vs 状态映射不一致

**矛盾点**:
| 来源 | `scheduled` 中文 | `confirmed` 中文 | `reported` 中文 |
|------|----------------|----------------|----------------|
| 文档 4.0.1（修正后） | 排产制定 | 排产确认 | 报工完成 |
| 流程模板 PROCESS_FLOW_TEMPLATES (步骤名) | 排产制定 | 排产确认 | 报工完成 |
| STATUS_KEY_TO_MYSQL (中文映射) | 已排产 | 已排产 | 质检中 |

**3 处定义 2 处不一致**，业务方按文档对照代码会困惑"为啥显示'质检中'但叫'报工完成'"。

**修复建议**: P0-3 同步修复后，本问题自动解决。

### 5.2 🟡 P1-11: 告警检测类型数量描述不准确

**文档 9.2 节**:
- 顶部表格"告警级别"列在第 1-8 项用 WARNING/CRITICAL/INFO 标注
- 实际 `alert_engine.py:179-671` 有 **12 个 check_ 函数**（含 1 个拆分前兼容入口 `check_order_timeout_alerts`）
- 顶部表格行号说"行 432/445/493"，但实际函数定义在 432/445/493 行（已确认）

**问题**:
- 9.2 第 1 段说"已拆分 (2026-06-20)"，但代码里 432 行 `check_order_timeout_alerts` 仍是"合并实现"注释
- 文档 9.2 标注"11 项"是按业务分类，实际函数有 12 个
- 自检标注"实际命中 10 个函数"是错的（实际 12 个）

**修复建议**:
- 9.2 节明确说明"11 类业务，12 个函数（1 个兼容入口）"
- 在 9.2 第 1 段标注"`check_order_timeout_alerts` 是兼容入口，业务实现走 `check_overdue_task_alerts` + `check_order_overdue_alerts`"

### 5.3 🟡 P1-12: 告警冷却时间参数不一致

**文档 9.3 节告警配置参数**:
- `alert_cooldown_minutes`: 30 分钟（默认）

**代码实际** (`alert_engine.py` 多处):
- 行 156: `cooldown = self._get_rules().get('alert_cooldown_minutes', 30)` ← 30 分钟
- 行 248: `cooldown = self._get_rules().get('alert_cooldown_minutes', 30)` ← 30 分钟
- 行 389: `cooldown = self._get_rules().get('alert_cooldown_minutes', 30)` ← 30 分钟
- 行 451: `cooldown = self._get_rules().get('alert_cooldown_minutes', 60)` ← ❌ 60 分钟
- 行 499: `cooldown = self._get_rules().get('alert_cooldown_minutes', 60)` ← ❌ 60 分钟
- 行 551: `cooldown = self._get_rules().get('alert_cooldown_minutes', 60)` ← ❌ 60 分钟

**问题**: `check_overdue_task_alerts`（行 445）、`check_order_overdue_alerts`（行 493）、`check_material_arrival`（行 546）用 60 分钟冷却，与文档默认 30 分钟不一致。

**修复建议**: 9.3 节增加"告警冷却时间覆盖"小节，列出 3 个用 60 分钟的特殊检测项。

### 5.4 🟡 P1-13: 物料字段命名跨库仍有歧义

**问题**: 3 节物料数据模型和 1.8 字段映射表都涉及"物料"，但命名混乱：

| 概念 | 移动端 material_records | 桌面端 order_materials |
|------|------------------------|----------------------|
| 需求数量 | `planned_qty` | `required_qty` |
| 已完成数量 | `completed_qty` | `prepared_qty` |
| 状态 | `status` | `prep_status` |
| 物料名 | `material_name` | `material_name` |

**业务问题**:
1. 移动端 `completed_qty` 含义是"已备料数量"，但字面意思像"已完成数量"（容易和 `process_sub_steps.completed_qty` 混淆）
2. 桌面端 `prep_status` 业务上指的是"备料状态"，但代码中 `prep_status` 值是中文（"待备料"/"备料中"/"已备料"），与 4.0.2 状态机中 `material_purchase` 流程的 `required/checked/approved/ordered/received/issued` 完全不映射

**修复建议**:
- 3.1 节增加"字段语义对照表"，明确每个字段的业务含义
- 4.0.2 `material_purchase` 流程的 6 个状态键 与 `prep_status` 业务值（待备料/备料中/已备料）的对应关系应在文档中说明

---

## 6. 第八章 任务回归审计系统专项审计

### 6.1 ✅ 路由完整性

| 回归类型 | 文档是否列 | 代码是否实现 | 评估 |
|---------|:---------:|:----------:|------|
| 质检回归 /quality-regression | ✅ | ✅ _core.py:6326 | ✅ |
| 物料回归 /material-regression | ✅ | ✅ _core.py:6346 | ✅ |
| 外协回归 /outsource-regression | ✅ | ✅ _core.py:6366 | ✅ |
| 排产回归 /schedule-regression | ✅ | ✅ _core.py:6386 | ✅ |
| 维修回归 /repair-regression | ❌ 文档未列 | ❌ 代码未实现 | 🟡 一致缺失 |
| 工序回归 /process-regression | ❌ 文档未列 | ❌ 代码未实现 | 🟡 一致缺失 |

**评估**: 4 个回归 API 与文档 8.2 一致。但根据 8.6 节"字段名映射规则"列了 5 个表（含 process_sub_steps），意味着工序应该也有回归 API。

**修复建议**:
- 选项 A: 8.6 删除 process_sub_steps 行（因为没回归 API）
- 选项 B: 增加 /process-regression 路由（参考 quality_regression 模式）

### 6.2 🟡 P1-14: 8.4 返回数据格式不准确

**文档 8.4 描述返回字段**:
```json
{
  "id": "REC001",
  "title": "工序名称 / 物料名称 / 外协标题",
  "operator": "操作员 / 质检员 / 供应商",
  "status": "pending|completed|withdrawn"
}
```

**代码实际**（_core.py:6326-6403）：
- `/quality-regression` 返回字段: `id, order_no, inspection_type, result, inspector, status, record_date`（**没有 title 字段**）
- `/material-regression` 返回字段: `id, order_no, material_name, target_operator, status, created_at`（**没有 title 字段**）
- `/outsource-regression` 返回字段: `id, order_no, title, supplier_name, status, created_at`（**有 title 字段**）
- `/schedule-regression` 返回字段: `id, order_no, status, created_at`（**没有 title 字段**）

**问题**: 8.4 文档把"title 字段"当作所有回归 API 的通用字段，但实际**只有 outsource 有 title**。

**修复建议**: 8.4 节改为按回归类型分别列字段：
- 质检回归: `id, order_no, inspection_type, result, inspector, status, record_date`
- 物料回归: `id, order_no, material_name, target_operator, status, created_at`
- 外协回归: `id, order_no, title, supplier_name, status, created_at`
- 排产回归: `id, order_no, status, created_at`

### 6.3 🟡 P1-15: 8.5 质检回归特殊字段描述片面

**文档 8.5 节**:
- 列出 `inspection_type/result/inspector/record_date` 4 个特殊字段
- 提示"注意：质检表用的是 record_date，不是 created_at"

**问题**: 实际 `_attach_order_status_sync(cur, rows, 'order_no')` 还会附加**订单状态字段**（8.4 节未提及），但 8.5 也没说明。

**修复建议**: 8.5 节增加"附加字段"段落，说明所有回归 API 都会附加订单状态（来自 `_attach_order_status_sync`）。

### 6.4 🟡 P1-16: 8.8.1 迁移状态矩阵存在误导

**文档 8.8.1 迁移状态矩阵中"维修"行**:
| 维修 | `repair_task` | `repair_records` | - | - | - | - |

**问题**:
- 4 列（移动端/容器中心/调度中心/统计引擎）全 `-`，意味着维修任务**未迁移到独立表**
- 但根据 8.8.2 第 8 项和 8.6 字段映射规则，**维修任务确实在 repair_records 表**（数据是有的，只是回归 API 没实现）
- 矩阵说"未迁移"会误导读者以为数据不存在

**修复建议**: 8.8.1 "维修"行改为"⚠️ 数据存在但回归 API 未实现"，与"无回归路由"对应。

---

## 7. 第九章 预警与告警系统专项审计

### 7.1 ✅ 告警 API 路由存在性

文档 9.5 列 11 个路由，代码 `_core.py` 实际命中：

| 路由 | 行号 | 存在 |
|------|:----:|:----:|
| /api/dispatch-center/alerts (GET) | 6654 | ✅ |
| /api/dispatch-center/alerts/&lt;id&gt;/dismiss (POST) | 6692 | ✅ |
| /api/dispatch-center/alerts/stats (GET) | 6715 | ✅ |
| /api/dispatch-center/alerts/&lt;id&gt;/ack (POST) | 6751 | ✅ |
| /api/dispatch-center/alerts/&lt;id&gt;/snooze (POST) | 6764 | ✅ |
| /api/dispatch-center/violations (GET) | 1796 | ✅ |
| /api/dispatch-center/violations/stats (GET) | 1826 | ✅ |
| /api/dispatch-center/violations/recent (GET) | 1847 | ✅ |
| /api/dispatch-center/violations (DELETE) | 1863 | ✅ |
| /api/dispatch-center/configs/alert_rules (GET) | 9578 | ✅ |
| /api/dispatch-center/configs/alert_rules (PUT) | 9601 | ✅ |

**评估**: ✅ 11/11 路由全部存在。

### 7.2 🔴 P0-7: 告警检测类型与函数数量不符

**文档 9.2 节**:
- 顶部表格标注"11 项检测类型"
- 自检段落说"grep -n 'def check_' alert_engine.py 实际命中 10 个函数"

**实际命中**（`grep -n "def check_" alert_engine.py`）:
```
179: check_overdue_tasks
241: check_stalled_tasks
293: check_queue_depth
316: check_operator_overload
349: check_completion_rate
383: check_schedule_overdue
432: check_order_timeout_alerts    ← 兼容入口
445: check_overdue_task_alerts
493: check_order_overdue_alerts
546: check_material_arrival
584: check_outsource_reminders
671: check_escalations
```
**实际: 12 个函数**，不是 10 个。

**问题**:
1. 文档自检"10 个函数"是错误
2. 11 类业务对应 12 个函数（多 1 个兼容入口），文档应说明清楚
3. alert_engine.py:782 调用方暂未变更（仅执行兼容入口），实际业务检测走的是 445+493 行的拆分函数

**修复建议**:
- 9.2 顶部说明改为"11 类检测，12 个函数（含 1 个向后兼容入口）"
- 删除 9.2 第 1 段错误描述"10 个函数"

### 7.3 🟡 P1-17: 9.6 前端实现章节过简

**问题**: 9.6 节只列了 2 个前端文件，没有说明：
- 告警通知的**触达用户**（谁收到群消息/应用消息）
- 告警**自动刷新**的具体实现（是否轮询/WebSocket）
- **告警升级**的可视化（CRITICAL 是否红色高亮）

**修复建议**: 9.6 增加"前端交互流程"小节，描述用户从登录到处理告警的完整路径。

### 7.4 🟡 P1-18: 9.4 告警发送渠道描述模糊

**文档 9.4 节**:
- 微信群：GroupBot 发送
- 应用消息：发给任务负责人
- 告警缓冲：非 CRITICAL 聚合发送

**问题**:
1. "应用消息发给任务负责人"**没说发到哪个 App**（企业微信？钉钉？短信？）
2. "告警缓冲"机制是**异步聚合**还是**队列**？文档没说
3. `_send_alert(msg, level='WARNING')` 实际是**直接发**，没看到"缓冲聚合"代码

**修复建议**: 9.4 补充：
- 应用消息 = 企业微信 App
- 告警缓冲 = 实际未实现（是文档愿景？），需要确认

---

## 8. 第三章 物料数据模型专项审计

### 8.1 ✅ 字段映射基本准确

1.8 节字段映射表与代码 `_core.py:9309-9313` 实际 material_field_map 完全一致（3 个字段）。✅

### 8.2 🟡 P1-19: 物料状态语义不清晰

**问题**: 3 节未说明"物料状态"在两库中的具体业务值：

| 数据库 | 状态字段 | 业务值（推测） |
|--------|---------|--------------|
| material_records (container_center) | `status` | 采购中/已下单/已到货/已领料？ |
| order_materials (steel_belt) | `prep_status` | 待备料/备料中/已备料 |

代码 `_core.py:2473` 显示 `prep_status IN ('待备料', '备料中', '已备料')`，但 `status` 的具体值未在文档中说明。

**修复建议**: 3 节增加"物料状态值映射表"：
- `status='采购中'` ↔ `prep_status='待备料'`
- `status='已到货'` ↔ `prep_status='备料中'`
- `status='已领料'` ↔ `prep_status='已备料'`

### 8.3 🟡 P1-20: 物料同步缺少冲突检测说明

**问题**: 3.1 节双向同步流程没有说明：
- 两端同时修改怎么办（最后写优先？合并？报警？）
- 网络中断后如何恢复（DLQ？本地缓存？）

**修复建议**: 3.1 增加"异常处理"小节。

---

## 9. 第十章 消息模板专项审计（汇总）

### 9.1 模板覆盖度问题汇总

| 问题 | 严重度 | 文档位置 | 修复建议 |
|------|:-----:|---------|---------|
| 模板清单仅覆盖 35% | 🔴 P0 | 10.1 | 扩展为完整 54 个 |
| 外协提醒未走模板引擎 | 🟡 P1 | 9.2 + 10.1 | 新增 `tmpl_outsource_reminder` |
| 10.4 调用方有"⚠️ 待核" | 🟡 P1 | 10.4 | 用 grep 精确定位函数名 |
| 10.2 接收人规则不完整 | 🟡 P1 | 10.2 | 与 10.4 对齐 |

### 9.2 模板渲染调用方完整度

**实际 _render_template 命中 18 处**（`grep -n "_render_template" _core.py`）：
```
1312: tmpl_task_urgent
1319: tmpl_task_delay
1379: 动态 template_id
1594: tmpl_process_start
2542: tmpl_task_assigned
2625: tmpl_task_transfer
2672: tmpl_task_cancelled
2743: tmpl_batch_assign
4302: tmpl_process_advance
4910: tmpl_repair_complete
6449: tmpl_outsource_send
6538: tmpl_outsource_receive
7086: tmpl_cost_loss_warning
7098: tmpl_cost_low_margin
7108: tmpl_cost_profitable
7704: tmpl_schedule_change
8820: tmpl_alert_quality
8929: tmpl_quality_completed
```

**与 10.4 节对比**:
- 10.4 列了 18+ 模板调用方，覆盖度较全 ✅
- 但缺 `tmpl_material_assigned`、`tmpl_outsource_assigned` 等的调用方（**这 2 个模板定义了但未在 _core.py 调用**）
- 需查 `services/notifier.py` 等其他文件确认

---

## 10. 问题汇总表

| # | 问题 | 严重度 | 涉及章节 | 修复优先级 |
|---|------|:-----:|:-------:|:---------:|
| 1 | 缺失"入库流程"模板 | 🔴 P0 | 4.0.2 | 高 |
| 2 | 缺失"派单中 DISPATCHED"状态 | 🔴 P0 | 4.0.1 | 高 |
| 3 | v3.6.4 状态机"修正"是虚假闭环 | 🔴 P0 | 4.0.1 | 高 |
| 4 | 两套状态体系并存 | 🔴 P0 | 4.0.1 + 全文 | 高 |
| 5 | 工序代码示例与代码不符 | 🔴 P0 | 4.1, 4.2 | 高 |
| 6 | 模板清单仅覆盖 35% | 🔴 P0 | 10.1 | 中 |
| 7 | 告警检测类型与函数数量不符 | 🔴 P0 | 9.2 | 中 |
| 8 | 排产流程未独立建模 | 🟡 P1 | 4.0.2 | 中 |
| 9 | 维修流程步骤与报修种类不一致 | 🟡 P1 | 4.1 | 中 |
| 10 | 状态机缺少回退路径 | 🟡 P1 | 4.0.3 | 中 |
| 11 | 质量记录状态机不齐 | 🟡 P1 | 4.0.3 | 中 |
| 12 | 4.2 流程图缺移动端节点 | 🟡 P1 | 4.2 | 中 |
| 13 | 3.1 物料同步缺异常处理 | 🟡 P1 | 3.1 | 中 |
| 14 | 3.2 字段映射表不完整 | 🔵 P2 | 3.2 | 低 |
| 15 | 外协提醒未走模板 | 🟡 P1 | 9.2, 10.1 | 中 |
| 16 | 10.4 调用方"⚠️ 待核" | 🟡 P1 | 10.4 | 中 |
| 17 | 10.2 接收人规则不全 | 🟡 P1 | 10.2 | 中 |
| 18 | 告警冷却时间不一致 | 🟡 P1 | 9.3 | 中 |
| 19 | 物料字段命名跨库歧义 | 🟡 P1 | 3 | 中 |
| 20 | 8.4 返回数据格式不准确 | 🟡 P1 | 8.4 | 中 |
| 21 | 8.5 缺附加字段说明 | 🟡 P1 | 8.5 | 低 |
| 22 | 8.8.1 迁移矩阵"维修"行误导 | 🟡 P1 | 8.8.1 | 低 |
| 23 | 9.6 前端实现章节过简 | 🟡 P1 | 9.6 | 低 |
| 24 | 9.4 告警渠道描述模糊 | 🟡 P1 | 9.4 | 低 |
| 25 | 物料状态语义不清晰 | 🟡 P1 | 3 | 中 |
| 26 | 物料同步缺冲突检测 | 🟡 P1 | 3.1 | 中 |

**统计**:
- 🔴 P0: 7 项
- 🟡 P1: 17 项
- 🔵 P2: 2 项
- **总计**: 26 项

---

## 11. 给后续迭代的建议

### 11.1 优先级排序

1. **第一波（P0 必修）**: 问题 1-7，7 个 P0 项
2. **第二波（P1 推荐）**: 问题 8-19，主要业务流修复
3. **第三波（P2 优化）**: 问题 20-26，文档细节完善

### 11.2 SSOT（Single Source of Truth）治理

| 建议 | 范围 | 难度 |
|------|------|:----:|
| 状态枚举统一用 `models/enums.py` 大写英文 | 全栈 | 中 |
| 流程模板统一用 `dispatch_center/_constants.py` | 调度中心 | 中 |
| 模板定义统一用 `template_engine.py` | 通知系统 | 低 |
| 工序代码统一用 `core/process_code_classifier.py` 规则 | 业务层 | 中 |

### 11.3 反"虚假闭环"建议

> **审计员观察**: 本次审计发现 v3.6.4 自我宣称"已闭环"的 P0-6（状态机修正）**实际未修改代码**。建议：
>
> 1. 待修改代码清单的"决议"列改为"待代码验证后闭环"
> 2. 每次文档版本发布前，必须用 `grep` 验证 3-5 个关键修复点
> 3. 增加"代码-文档一致性"审计环节，作为 v3.6.5 必修

---

## 12. 附录：审计方法说明

### 12.1 验证命令清单

```bash
# 1. 状态键定义
grep -n "STATUS_KEY_TO_MYSQL" mobile_api_ai/dispatch_center/_constants.py
grep -n "PROCESS_FLOW_TEMPLATES" mobile_api_ai/dispatch_center/_constants.py

# 2. 流程模板
grep -n "'production'\|'material_purchase'\|'quality'\|'repair'\|'outsource'" mobile_api_ai/dispatch_center/_constants.py

# 3. 枚举类
cat models/enums.py

# 4. 回归 API
grep -n "regression" mobile_api_ai/dispatch_center/_core.py

# 5. 告警检测函数
grep -n "def check_" mobile_api_ai/container_center/services/alert_engine.py

# 6. 告警 API 路由
grep -n "@dispatch_center_bp.route" mobile_api_ai/dispatch_center/_core.py | grep "alert\|violation"

# 7. 模板定义
grep -n "'id': 'tmpl_" mobile_api_ai/template_engine.py

# 8. 模板调用
grep -n "_render_template" mobile_api_ai/dispatch_center/_core.py

# 9. 字段映射
grep -n "field_map" mobile_api_ai/dispatch_center/_core.py

# 10. 工序代码
cat mobile_api_ai/core/process_code_classifier.py
```

### 12.2 关键文件路径

| 文件 | 行数 | 作用 |
|------|:----:|------|
| `mobile_api_ai/docs/ARCHITECTURE_v3.6.md` | 1470 | 被审计文档 |
| `mobile_api_ai/dispatch_center/_constants.py` | 140 | 状态键、流程模板定义 |
| `mobile_api_ai/models/enums.py` | 157 | 枚举类（OrderStatus/ProductionStatus 等） |
| `mobile_api_ai/dispatch_center/_core.py` | ~9600 | 调度中心核心（含 4 个回归 API + 11 个告警 API） |
| `mobile_api_ai/container_center/services/alert_engine.py` | 782 | 告警引擎（12 个 check 函数） |
| `mobile_api_ai/template_engine.py` | 401+ | 模板引擎（54 个模板 ID） |
| `mobile_api_ai/core/process_code_classifier.py` | 100+ | 工序代码分类规则 |
| `mobile_api_ai/container_config.py` | 250+ | 容器配置（工序、报修种类） |

---

## 13. 审计员签字

> **本次审计覆盖**: ARCHITECTURE_v3.6.md 第 3/4/8/9/10 章共 5 个章节
>
> **审计方式**: 文档逐节研读 + Grep 代码反向验证（10+ 个核心命令）
>
> **审计时长**: 约 45 分钟
>
> **审计结论**: 文档整体**结构清晰、版本治理有序**，但存在 **7 个 P0 严重问题**（其中 1 个是"虚假闭环"），需要下一轮迭代集中修复
>
> **审计员**: 小曦（产品经理）
>
> **日期**: 2026-06-23

---

**报告结束**
