# 品控师审计报告 - ARCHITECTURE_v3.6.md

> **审计人**: 品控师小贺（20年工厂管理经验 + 软件品控能力）
> **审计对象**: `d:\yuan\不锈钢网带跟单3.0\mobile_api_ai\docs\ARCHITECTURE_v3.6.md`
> **审计范围**: 1.4 服务间通信约束（R-001/R-002/R-003）/ 4.0.1 状态键定义 / 2.3 归档机制 SLA / 命名规范 / 错误码规范 / 规则引用一致性
> **审计日期**: 2026-06-23
> **审计性质**: 仅文档品控，不修改任何源代码与架构文档本身

---

## 0. 品控师总评

| 维度 | 评级 | 关键发现 |
|------|:----:|----------|
| **规则引用一致性** | 🔴 严重不合格 | **R-003 表述与 PROJECT_ITERATION_RULES.md 完全不一致**（两条互不相关的规则共用同一编号） |
| **状态值/枚举一致性** | 🔴 严重不合格 | 状态机存在 4 套互相矛盾的定义（PROJECT_ITERATION_RULES.md / ARCHITECTURE_v3.6.md 4.0.1 / `constants.py` / `_constants.py`），且 v3.6.4 修正后文档与代码继续相悖 |
| **SLA 表述精度** | 🟡 一般不合格 | "≤10s" 的承诺在 P0-2（DLQ retry worker 缺失）未修复前不可信；2.3.5 写"T+1~5s"无依据 |
| **错误码规范一致性** | 🔴 严重不合格 | PROJECT_ITERATION_RULES.md 附录A 定义 5 段（1xxx~5xxx），但 core/error_codes.py 实际使用 6 段（含 E1xxx~E1xxx 业务领域细分、E2xxx 校验失败） |
| **服务端口一致性** | 🟡 一般不合格 | 1.2 表只列 4 端口，1.1 架构图与 6.7.2 列 7 端口；core/_config_infra.py 配置默认端口与文档不符 |
| **命名规范执行** | 🟡 一般不合格 | 状态值出现"中英文混用"，无统一约束声明 |

**主线目标**：🔴 **不合规**——文档在 4 处核心规则（R-003、状态机、错误码段位、端口表）上与权威源（PROJECT_ITERATION_RULES.md 与实际代码）矛盾。

---

## 1. 规则表述问题清单

### 🔴 P1-R1.1 R-003 严重错位（高优先级）

| 字段 | 内容 |
|------|------|
| **位置** | ARCHITECTURE_v3.6.md 1.4 节 |
| **现状** | R-003 = "移动端更新后必须通过 5003 调度中心同步到桌面端" |
| **权威源** | PROJECT_ITERATION_RULES.md 第 29 行：R-003 = "新增服务必须向 5003 调度中心注册，遵循统一路由规范" |
| **影响** | 同一编号承载两条**完全不同**的规则——一条是"注册流程"，一条是"同步约束"，审计/合规检查无所适从 |
| **建议** | 二选一：(a) 在 ARCHITECTURE_v3.6.md 新增 R-003a/003b；(b) 同步两文档，确立单一权威源 |
| **证据** | `PROJECT_ITERATION_RULES.md:29` `ARCHITECTURE_v3.6.md:147` |

### 🟡 P1-R1.2 R-002 表述细节差异（中优先级）

| 字段 | 内容 |
|------|------|
| **位置** | ARCHITECTURE_v3.6.md 1.4 节 R-002 |
| **现状** | "所有云端通信必须通过 5003 调度中心转发到**云端 5006**" |
| **权威源** | PROJECT_ITERATION_RULES.md 第 28 行：仅写"通过 5003 调度中心转发"，**未提"5006"** |
| **影响** | 表面看是 ARCHITECTURE 加了细节，但若未来云端端口变化，需同步两文档 |
| **建议** | 在 PROJECT_ITERATION_RULES.md 同步补"云端 5006"细节，或 ARCHITECTURE 改回原句 |
| **证据** | `PROJECT_ITERATION_RULES.md:28` `ARCHITECTURE_v3.6.md:146` |

### 🟢 P1-R1.3 R-001 表述一致（已确认）

| 字段 | 内容 |
|------|------|
| **位置** | ARCHITECTURE_v3.6.md 1.4 节 R-001 |
| **权威源对比** | PROJECT_ITERATION_RULES.md 第 27 行 |
| **结果** | ✅ **完全一致**："禁止在服务 A 中直接连接服务 B 的数据库，必须通过 API 接口交互" |
| **关联风险** | ⚠️ R-001 实际在 `models/order.py:52-99` 仍被违反（Q-B2 待处理），文档规则无错但执行层失守 |

---

## 2. 状态值/枚举一致性问题（最严重）

### 🔴 P1-S2.1 状态机定义四套并存（高优先级）

| # | 来源 | 状态定义 | 步骤数 | 备注 |
|---|------|----------|:------:|------|
| 1 | `PROJECT_ITERATION_RULES.md:146` 订单生命周期 | created → **confirmed** → **scheduled** → in_progress → completed → shipped → archived | 7 | 顺序：**confirmed 在 scheduled 前** |
| 2 | `ARCHITECTURE_v3.6.md:524` 4.0.1 状态键 | published → **scheduled** → **confirmed** → in_production → reported → qc_passed → completed | 7 | 顺序：**scheduled 在 confirmed 前**（与源 1 相反） |
| 3 | `constants.py:9-22` OrderStatus 枚举 | PENDING→CONFIRMED→PENDING_PUBLISH→PUBLISHED→SCHEDULED→PRODUCTION→QC→FINISHED→PACKED→PENDING_SHIP→SHIPPED→CANCELLED | 12 | 与上两套完全不同（多了 PACKED / QC / PENDING_PUBLISH 等） |
| 4 | `mobile_api_ai/dispatch_center/_constants.py:14-22` STATUS_KEY_TO_MYSQL | published→scheduled→confirmed→in_production→reported→qc_passed→completed | 7 | 英文 key 与文档 4.0.1 一致，但**状态值用中文"已排产"两态共用** |

**影响**：
- 桌面端、容器中心、移动端、调度中心各自引用不同定义的状态枚举
- 跨服务同步时（如 1.8 字段映射）状态值映射极易出错
- 文档 4.0.3 状态流图与实际代码逻辑不一定匹配

**证据**：
- `PROJECT_ITERATION_RULES.md:146`
- `ARCHITECTURE_v3.6.md:524-549`
- `constants.py:9-22`
- `mobile_api_ai/dispatch_center/_constants.py:14-22`

### 🔴 P1-S2.2 v3.6.4 "scheduled/confirmed" 修正与代码相悖（高优先级）

| 字段 | 内容 |
|------|------|
| **位置** | ARCHITECTURE_v3.6.md 4.0.1 + 4.0.4 + P0-6 决议 |
| **文档声明** | v3.6.4 修正后：`scheduled` = 排产**制定** / `confirmed` = 排产**确认** |
| **代码现状** | `_constants.py:16-17`：`'scheduled': '已排产'` 与 `'confirmed': '已排产'`（**两个 key 映射到同一中文值**） |
| **影响** | 文档说"消除歧义"，但代码实际是**更歧义**——两个状态 key 在 MySQL 中根本无法区分 |
| **建议** | 若要落实 v3.6.4 修正，必须同时改 `_constants.py`：scheduled→"排产制定"、confirmed→"排产确认" |
| **证据** | `ARCHITECTURE_v3.6.md:498-499` vs `_constants.py:16-17` |

### 🟡 P1-S2.3 状态机步骤数声明与流程模板不一致（中优先级）

| 字段 | 内容 |
|------|------|
| **位置** | ARCHITECTURE_v3.6.md 4.0.1 状态键定义（7 个）vs 4.0.2 流程模板（5 个流程） |
| **问题** | 4.0.2 表格声明 5 个流程（production/material_purchase/quality/repair/outsource），但 4.0.3 中质量流程只有 4 步（`quality_received → quality_judged → quality_approved → completed`），文档 4.0.1 状态键 7 项未在 quality 流程中体现任何 |
| **影响** | 文档 4.0.1 是"通用"状态键，4.0.3 是"具体"流程流，但两者未做映射声明 |
| **建议** | 在 4.0.4 加映射表："production 流程使用 scheduled/confirmed/in_production/reported/qc_passed/completed"等 |

### 🔴 P1-S2.4 工序任务状态机缺失（高优先级）

| 字段 | 内容 |
|------|------|
| **位置** | ARCHITECTURE_v3.6.md 4.0.1 缺失 |
| **问题** | PROJECT_ITERATION_RULES.md 第 160 行定义了工序任务状态流：`待发布(pending) → 已发布(distributed) → 执行中(in_progress) → 已完成(completed)`，但 ARCHITECTURE_v3.6.md 4.0.1 完全没有该状态机的定义或引用 |
| **影响** | 文档章节名为"状态机定义"，但只覆盖了订单状态，工序状态（更频繁变动的部分）未在统一章节定义 |
| **建议** | 在 4.0.1 增加"工序任务状态机"小节或显式声明"工序状态机见 PROJECT_ITERATION_RULES.md 第 160 行" |

### 🟡 P1-S2.5 质检/外协/物料 4 状态机 vs 实际 R-070 多状态

| 字段 | 内容 |
|------|------|
| **位置** | ARCHITECTURE_v3.6.md 4.0.3 |
| **问题** | 4.0.3 物料流程 6 步：`required → checked → approved → ordered → received → issued`，但 PROJECT_ITERATION_RULES.md 第 174 行物料发布 4 步：`material_requested → material_confirmed → material_arrived → material_delivered`，两者完全不同（命名不同、步数不同） |
| **影响** | 文档自相矛盾且与权威规则源不一致 |
| **建议** | 二选一统一：要么以 4.0.3 为准，4 步合并到 6 步；要么以 PROJECT_ITERATION_RULES.md 为准 |

---

## 3. SLA 表述问题

### 🔴 P1-L3.1 "≤10s" 承诺在 P0-2 修复前不可信（高优先级）

| 字段 | 内容 |
|------|------|
| **位置** | ARCHITECTURE_v3.6.md 2.3.4 "缓存清除，**预计 ≤10s**" |
| **承诺链路** | 归档 → emit_invalidate → DLQ → 5003 → 缓存清除 |
| **代码事实** | `_reconcile.py:18` 默认对账间隔 `_RECONCILE_INTERVAL = 600`（10 分钟）；P0-2 决议："DLQ retry worker **缺失**" |
| **实际最坏情况** | DLQ 5 次重试：1s + 2s + 4s + 8s + 16s = 31s（首次延迟 + 重试退避总和）**远超 10s** |
| **影响** | "≤10s" SLA 在 P0-2 修复前是**虚假承诺**，对账 worker 兜底是 10 分钟级别 |
| **建议** | 改为分层 SLA："DLQ 链路 ≤5s 到达 5003，但需 P0-2 修复后才保证 5 次重试 100% 到达；当前未修复时，依赖对账 worker 10 分钟兜底" |
| **证据** | `ARCHITECTURE_v3.6.md:377` `_reconcile.py:18` ARCHITECTURE_v3.6.md:30 (P0-2) |

### 🟡 P1-L3.2 2.3.5 写"T+1~5s"无依据（中优先级）

| 字段 | 内容 |
|------|------|
| **位置** | ARCHITECTURE_v3.6.md 2.3.5 ASCII 图 |
| **问题** | "缓存清除（T+1~5s）"——这个数字来源不明，未引用代码或测试数据 |
| **影响** | 增加文档表面精度反而误导读者（看似精确但无依据） |
| **建议** | 改为"T+秒级（具体数值依赖 DLQ retry worker 实际表现，建议 v3.6.5 补压测数据）" |

### 🟢 P1-L3.3 文档"立即生效"概念引入正确（已闭环）

| 字段 | 内容 |
|------|------|
| **位置** | ARCHITECTURE_v3.6.md 2.3.4 表头 |
| **评价** | ✅ v3.6.4 修正后"数据库状态变更（毫秒级 T+0s）"和"缓存清除（秒级~分钟级）"两个概念区分准确 |
| **保留建议** | 这是 v3.6.4 的最大改进点，应继续作为归档机制表述范本 |

### 🟡 P1-L3.4 "对账 worker 10 分钟"标注缺失来源

| 字段 | 内容 |
|------|------|
| **位置** | ARCHITECTURE_v3.6.md 2.3.4 "由对账 worker 兜底，最长 10 分钟" |
| **问题** | "10 分钟"未明确来源，应注明"`_reconcile.py:18` 的 `_RECONCILE_INTERVAL = 600` 秒" |
| **影响** | 未来若调整对账间隔，文档与代码无双向追溯 |
| **建议** | 在表格脚注加 "**来源**: `_reconcile.py:18` `_RECONCILE_INTERVAL=600`" |

---

## 4. 命名规范问题

### 🟡 P1-N4.1 状态值中英文混用

| 字段 | 内容 |
|------|------|
| **位置** | ARCHITECTURE_v3.6.md 4.0.1 状态键定义 |
| **现状** | 状态键：英文 snake_case（`published`/`scheduled`/`confirmed` 等）✅ 符合 R-020<br>状态值：中文（"已发布"/"排产制定"/"排产确认"）|
| **问题** | R-020 "禁止使用拼音命名"只约束了拼音，未约束"中英文混用" |
| **影响** | 跨语言团队（中/英）易出现状态值字面量不一致（如"已发布" vs "已下发"） |
| **建议** | 明确声明：状态值是"展示用中文"还是"代码用英文"——在文档 4.0.1 表头加"状态键为代码存储值（snake_case），状态值为 UI 展示用（中文）" |

### 🔴 P1-N4.2 状态值用同一中文映射两个 key（高优先级）

| 字段 | 内容 |
|------|------|
| **位置** | `_constants.py:16-17` |
| **问题** | `'scheduled': '已排产'` 与 `'confirmed': '已排产'` 同值 |
| **影响** | 如果有外部系统查询 "已排产"，会同时匹配两个状态，无法区分；调度中心→MySQL 同步时"已排产"含义丢失 |
| **建议** | 修改代码落实 v3.6.4 修正（见 P1-S2.2） |

### 🟢 P1-N4.3 数据库字段命名规范符合 R-021/R-022

| 字段 | 内容 |
|------|------|
| **位置** | 文档 2.2 核心表清单 |
| **评价** | ✅ 表名/字段名均使用 snake_case（`order_no` / `created_at`），符合 R-021/R-022 |
| **无需变更** | — |

### 🟡 P1-N4.4 错误码命名规范无章节级声明

| 字段 | 内容 |
|------|------|
| **位置** | ARCHITECTURE_v3.6.md 全文 |
| **问题** | 文档无章节说明"错误码命名规范"（如 E 前缀规则、段位映射、5xxx 业务错误用法） |
| **影响** | 新增错误码时无统一规则可循 |
| **建议** | 增加 4.0.5 错误码命名规范小节，引用 PROJECT_ITERATION_RULES.md 附录A + 补 E 前缀约定 |

---

## 5. 错误码规范问题

### 🔴 P1-E5.1 错误码段位定义与实际不符（高优先级）

| 字段 | 内容 |
|------|------|
| **权威源** | PROJECT_ITERATION_RULES.md 附录A：<br>0 成功<br>1001-1999 参数错误 (1xxx)<br>2001-2999 认证授权 (2xxx)<br>3001-3999 业务逻辑 (3xxx)<br>4001-4999 资源不存在 (4xxx)<br>5001-5999 系统内部 (5xxx) |
| **代码实际** | `core/error_codes.py:163-716` 实际使用：<br>E0001-E0006 系统语法<br>E0101-E0109 数据库错误<br>E0201-E0204 导入/模块<br>E0301-E0304 安全<br>E0401-E0405 数据校验<br>E0501-E0504 业务错误<br>E0601-E0604 资源错误<br>E0701-E0703 网络错误<br>**E1001-E1006** 订单领域<br>**E1101-E1105** 生产领域<br>**E1201-E1204** 质量领域<br>**E1301-E1304** 库存领域<br>**E1401-E1404** 认证领域<br>**E2001** 校验失败<br>**E3001** 数据库错误 |
| **冲突点** | 1. **段位冲突**：附录A 说 1xxx=参数错误，但 E1001 是"订单未找到"（应是 4xxx 资源不存在）；E1005 是"订单状态不允许"（应是 3xxx 业务逻辑）<br>2. **段位重复**：E2xxx 既是"认证授权"（附录A）又是"校验失败"（error_codes.py E2001）；E3xxx 既是"业务逻辑"（附录A）又是"数据库错误"（error_codes.py E3001）<br>3. **格式冲突**：附录A 暗示纯数字（1001），代码使用 E 前缀字符串（E1001）<br>4. **段位数不同**：附录 5 段，代码 6 段（含业务领域细分 E1xxx）|
| **影响** | 不同模块使用错误码时无统一段位可循；前端做错误码处理时无映射表 |
| **建议** | 二选一：<br>(a) 改 PROJECT_ITERATION_RULES.md 附录A，反映实际段位（E0xxx 系统/E1xxx 业务领域/E2xxx 校验/E3xxx 数据库/E4xxx 资源/E5xxx 网络）<br>(b) 改 core/error_codes.py，按附录A 重新分配 |
| **证据** | `PROJECT_ITERATION_RULES.md:601-606` `core/error_codes.py:163-716` |

### 🟡 P1-E5.2 错误响应格式示例与实际不符（中优先级）

| 字段 | 内容 |
|------|------|
| **权威源** | PROJECT_ITERATION_RULES.md 第 222-226 行：`{"code": 1001, "message": "订单不存在", "data": null}` |
| **ARCHITECTURE** | 5.2 节：`{"code": 0, "message": "成功", "data": {...}}` |
| **代码实际** | `mobile_api_ai/app.py:155-157` 错误响应：`{'code': 401, 'message': '...'}`（**无 data 字段**）<br>`{'code': 500, 'message': str(e)}`（**无 data 字段**） |
| **问题** | 1. PROJECT_ITERATION_RULES.md 错误码 1001（业务错误）vs app.py 用 401（HTTP 状态码）<br>2. 错误响应格式三处定义不一致（有/无 data 字段） |
| **建议** | 统一为：成功 `{code:0, message:"...", data:{...}}` / 失败 `{code:xxxx, message:"...", data:null}`（PROJECT_ITERATION_RULES.md 示例是规范的） |

### 🟢 P1-E5.3 E 前缀格式文档未声明

| 字段 | 内容 |
|------|------|
| **问题** | PROJECT_ITERATION_RULES.md 附录A 用纯数字格式（1001），core/error_codes.py 用 E 前缀（E1001） |
| **建议** | 在附录A 加注 "**格式**: 实际代码使用 E 前缀字符串，附录列出数字部分" |

---

## 6. 服务端口与文件结构问题

### 🟡 P1-P6.1 1.1 架构图 / 1.2 端口表 / 6.7.2 端口表 三处不统一

| # | 章节 | 端口列表 |
|---|------|----------|
| 1 | 1.1 架构图 | 5000 / 5002 / 5003 / 5006 / 5008 / 5009 / 5010 / 8008（8 个） |
| 2 | 1.2 端口表 | 5002 / 5003 / 5008 / 5010（**只 4 个**） |
| 3 | 6.7.2 端口表 | 5000 / 5002 / 5003 / 5008 / 5009 / 5010 / 8008（7 个） |
| **冲突** | 1.1 有 5006（云端），1.2 和 6.7.2 没有；1.2 缺 5000/5009/8008 |
| **建议** | 在 1.2 表头加"完整端口列表见 6.7.2"，1.2 只列核心业务端口 |

### 🔴 P1-P6.2 core/_config_infra.py 端口默认值与文档不符（高优先级）

| 字段 | 内容 |
|------|------|
| **位置** | `core/_config_infra.py:184-192` |
| **实际配置** | `'sync_bridge': 'http://127.0.0.1:5005'`（文档说 8008）<br>`'inventory_api': 'http://127.0.0.1:5004'`（文档说 5010） |
| **代码实端口** | `sync_bridge_server.py:184` `port = int(os.getenv('PORT', 8008))` ✅ 8008<br>`inventory_api_server.py:430` `port = int(os.getenv('INVENTORY_API_PORT', '5010'))` ✅ 5010 |
| **矛盾** | 配置文件默认值错误：URL 写 5005/5004，实际服务跑 8008/5010——若不显式覆盖环境变量，会指向**错误服务** |
| **影响** | 容器中心 → 库存 / sync_bridge 跨服务调用可能连接到错误端口 |
| **建议** | 在 1.4 节加 ⚠️ 注意："`core/_config_infra.py` 默认 URL 与实际端口不一致，必须通过环境变量覆盖" |

### 🟡 P1-P6.3 5001 端口完全未在文档出现

| 字段 | 内容 |
|------|------|
| **现状** | `scripts/test_full_ux.py:18` `BASE = "http://127.0.0.1:5001"`<br>`scripts/test_ux_xiaoxi.py:35` `BASE = "http://localhost:5001"` |
| **问题** | 5001 端口用于测试/桌面端 Web 替代版，文档未声明 |
| **建议** | 在 6.7.2 端口表加 5001 端口条目（如"桌面 Web 替代版（测试用）"） |

---

## 7. 文档自相矛盾问题

### 🔴 P1-D7.1 版本号不一致（高优先级）

| 字段 | 内容 |
|------|------|
| **位置** | PROJECT_ITERATION_RULES.md 附录B 第 620 行 |
| **问题** | 写"当前版本：`v3.x.x`" |
| **实际版本** | 文档标题 v3.6.4（2026-06-23） |
| **建议** | 同步为 v3.6.4 |

### 🟡 P1-D7.2 1.6 同步端点表缺字段

| 字段 | 内容 |
|------|------|
| **位置** | ARCHITECTURE_v3.6.md 1.6 同步 API 端点 |
| **问题** | 1.6 表有 5 个端点（sub-step-report/material/repair/outsource/quality-record），但 1.5 同步架构图引用了 4 个端点（sub-step-report/material/repair/outsource），缺 quality-record；6.7.4 引用的是"容器中心→调度中心失效事件"，无 1.6 端点；Q-B1 已识别 |
| **建议** | 1.5 架构图补 quality-record 端点 |

### 🟡 P1-D7.3 待修改代码清单版本号标注错误

| 字段 | 内容 |
|------|------|
| **位置** | ARCHITECTURE_v3.6.md 头部 "**当前版本：v3.6.4**" vs 标题"v3.6" |
| **问题** | 修订历史表第 14 行"v3.6"无日期，标题 "v3.6"，但正文写"v3.6.4" |
| **建议** | 修订历史表第 14 行补 v3.6 实际日期；或合并到 v3.6.4 |

### 🟡 P1-D7.4 修订历史日期与正文日期一致性

| 字段 | 内容 |
|------|------|
| **位置** | ARCHITECTURE_v3.6.md 修订历史 |
| **现状** | 2026-06-23 出现 3 次（v3.6.1 / v3.6.2 / v3.6.3 / v3.6.4），无明确时序 |
| **建议** | 加 commit hash 或具体时分（HH:mm）区分 |

### 🟡 P1-D7.5 6.2 启动脚本目录注释不一致

| 字段 | 内容 |
|------|------|
| **位置** | ARCHITECTURE_v3.6.md 6.1 项目根目录 vs 6.7 项目运行方式 |
| **问题** | 6.1 列出 start_servers.py / start.py / start_services.py / start_*.py 等多个启动脚本，6.7.1 推荐 server_launcher.py；6.1 注释 `start_8008` 与 6.7.2 表中无 start_8008 引用 |
| **建议** | 6.1 启动脚本清单标"⚠️ 已废弃"或标"备用"避免误用 |

---

## 8. 整体问题优先级矩阵

| 优先级 | 问题编号 | 类别 | 标题 | 影响范围 |
|:------:|----------|------|------|----------|
| 🔴 P0 | P1-R1.1 | 规则引用 | R-003 严重错位（两套不相关规则共用编号） | 跨文档合规、审计 |
| 🔴 P0 | P1-S2.1 | 状态值 | 状态机四套并存 | 跨服务数据一致 |
| 🔴 P0 | P1-S2.2 | 状态值 | v3.6.4 修正与代码相悖 | 文档/代码双向失真 |
| 🔴 P0 | P1-S2.4 | 状态值 | 工序任务状态机缺失 | 工序管理一致性 |
| 🔴 P0 | P1-E5.1 | 错误码 | 错误码段位定义与实际不符 | 错误处理、API 文档 |
| 🔴 P0 | P1-P6.2 | 端口 | core/_config_infra.py 默认 URL 错配 | 跨服务调用可靠性 |
| 🔴 P0 | P1-D7.1 | 文档 | 版本号不一致 | 文档版本管理 |
| 🔴 P1 | P1-S2.5 | 状态值 | 物料/质检/外协 4 状态机矛盾 | 跨流程 |
| 🟡 P1 | P1-R1.2 | 规则引用 | R-002 表述细节差异 | 规则一致性 |
| 🟡 P1 | P1-L3.1 | SLA | ≤10s 承诺在 P0-2 修复前不可信 | 业务 SLA 承诺 |
| 🟡 P1 | P1-L3.2 | SLA | "T+1~5s" 无依据 | 文档可信度 |
| 🟡 P1 | P1-L3.4 | SLA | 对账 10 分钟缺来源 | 文档可追溯性 |
| 🟡 P1 | P1-S2.3 | 状态值 | 状态键 7 项 vs 流程模板 5 个未映射 | 文档完整性 |
| 🟡 P1 | P1-N4.1 | 命名 | 状态值中英文混用无声明 | 命名规范 |
| 🟡 P1 | P1-N4.2 | 命名 | 状态值用同一中文映射两个 key | 数据一致性 |
| 🟡 P1 | P1-N4.4 | 命名 | 错误码命名规范无章节 | 新增错误码无规 |
| 🟡 P1 | P1-E5.2 | 错误码 | 错误响应格式示例与实际不符 | API 规范 |
| 🟡 P1 | P1-E5.3 | 错误码 | E 前缀格式文档未声明 | 命名规范 |
| 🟡 P1 | P1-P6.1 | 端口 | 1.1/1.2/6.7.2 三处不统一 | 文档一致性 |
| 🟡 P1 | P1-P6.3 | 端口 | 5001 端口未在文档出现 | 文档完整性 |
| 🟡 P1 | P1-D7.2 | 文档 | 1.5 架构图缺 quality-record | 文档完整性 |
| 🟡 P1 | P1-D7.3 | 文档 | 标题与修订历史 v3.6 vs v3.6.4 不一致 | 文档版本管理 |
| 🟡 P1 | P1-D7.4 | 文档 | 修订历史日期时序不明 | 文档管理 |
| 🟡 P1 | P1-D7.5 | 文档 | 启动脚本清单无标记 | 文档准确性 |

---

## 9. 品控师建议（不修改，仅建议）

### 9.1 必须修复（P0 - 7 项）

1. **R-003 重新编号**：PROJECT_ITERATION_RULES.md 与 ARCHITECTURE_v3.6.md 二选一确立权威源，另一文档引用并标注差异
2. **状态机 SSOT（Single Source of Truth）**：建议以 `constants.py` 的 OrderStatus 枚举为权威源，统一文档、代码、同步映射
3. **v3.6.4 修正必须配套改代码**：`_constants.py:16-17` 两个 key 映射同值的 BUG 必须修，否则文档"消除歧义"承诺落空
4. **错误码段位 SSOT**：在 PROJECT_ITERATION_RULES.md 附录A 增加"实际段位映射表"，承认代码 6 段（E0xxx-E7xxx）
5. **`core/_config_infra.py` 默认 URL 修复**：sync_bridge 5005 → 8008，inventory_api 5004 → 5010
6. **附录B 版本号同步**：`v3.x.x` → `v3.6.4`
7. **工序任务状态机补全**：在 4.0.1 增加"工序任务"小节，引用 PROJECT_ITERATION_RULES.md 第 160 行

### 9.2 应该修复（P1 - 17 项）

详见第 8 节矩阵，**最高优先级 3 项**：
- L3.1（SLA 虚假承诺）
- E5.2（错误响应格式三处不一致）
- P6.1（端口表三处不统一）

### 9.3 建议改进（文档治理长期）

1. 增加 `docs/v3.6.5/状态机_SSOT_决策记录.md` —— 把状态机权威源决策过程留痕
2. 增加 `docs/SLA_承诺清单.md` —— 区分"代码保证"和"业务期望"
3. 增加 `docs/错误码_段位映射表.md` —— 错误码使用指南
4. 在 ARCHITECTURE_v3.6.md 顶部加"权威源声明"段：

```
| 文档/源 | 权威范围 |
|---------|----------|
| PROJECT_ITERATION_RULES.md | 强制规则 (R-001~R-243) |
| ARCHITECTURE_v3.6.md | 架构、状态机定义、API 端点 |
| constants.py | 代码层枚举（OrderStatus 等） |
| core/_config_infra.py | 运行时配置（端口、URL、连接） |
| mobile_api_ai/dispatch_center/_constants.py | 调度中心运行时状态映射 |
```

---

## 10. 一句话总结（品控师视角）

> **ARCHITECTURE_v3.6.md 在 7 项 P0 关键问题（特别是 R-003 错位、状态机四套并存、错误码段位与实际不符、配置默认 URL 错配）上与 PROJECT_ITERATION_RULES.md 和实际代码存在严重不一致，必须在下一迭代（v3.6.5）启动前完成文档治理，否则会持续误导新人并扩大与代码的偏差。**

---

## 附录 A：审计证据索引

| 证据编号 | 文件:行号 | 关键内容 |
|----------|-----------|----------|
| E-001 | `PROJECT_ITERATION_RULES.md:27-29` | R-001/R-002/R-003 权威定义 |
| E-002 | `ARCHITECTURE_v3.6.md:144-147` | ARCHITECTURE 1.4 节 R-001/R-002/R-003 |
| E-003 | `ARCHITECTURE_v3.6.md:493-509` | 4.0.1 + 4.0.4 状态键定义（v3.6.4 修正版） |
| E-004 | `mobile_api_ai/dispatch_center/_constants.py:14-22` | STATUS_KEY_TO_MYSQL 实际值 |
| E-005 | `constants.py:9-22` | OrderStatus 枚举（12 状态） |
| E-006 | `models/enums.py:12-33` | OrderStatus Enum（5 状态英文大写） |
| E-007 | `PROJECT_ITERATION_RULES.md:146` | 订单生命周期 7 状态权威定义 |
| E-008 | `PROJECT_ITERATION_RULES.md:160` | 工序任务状态机 4 步 |
| E-009 | `PROJECT_ITERATION_RULES.md:172-179` | 4 大发布流程状态机 |
| E-010 | `mobile_api_ai/dispatch_center/_reconcile.py:18` | 对账 worker 间隔 600s |
| E-011 | `core/_config_infra.py:184-192` | SERVICE_URLS 默认 URL（错配） |
| E-012 | `mobile_api_ai/sync_bridge_server.py:184` | 实际 sync_bridge 端口 8008 |
| E-013 | `mobile_api_ai/inventory_api_server.py:430` | 实际 inventory 端口 5010 |
| E-014 | `models/order.py:52-99` | R-001 实际违反（Q-B2） |
| E-015 | `core/error_codes.py:163-716` | ERRORS 实际定义（6 段位） |
| E-016 | `PROJECT_ITERATION_RULES.md:601-606` | 错误码附录A 5 段位定义 |
| E-017 | `PROJECT_ITERATION_RULES.md:218-225` | 响应格式权威示例 |
| E-018 | `mobile_api_ai/app.py:155-157` | app.py 实际错误响应（无 data 字段） |
| E-019 | `PROJECT_ITERATION_RULES.md:620` | 附录B 版本号 v3.x.x |
| E-020 | `ARCHITECTURE_v3.6.md:3` | 文档当前版本 v3.6.4 |

---

**审计结束**。

> **品控师小贺批注**：本次审计仅对文档做"信息准确性和规则合规性"评估，**不修改 ARCHITECTURE_v3.6.md 任何字符，不修改任何源代码**。审计报告输出到 `docs/v3.6.4文档治理/AUDIT_XIAOHE_品控师.md`，供下次 v3.6.5 迭代修复使用。建议优先级：P0 7 项必须在 v3.6.5 启动前闭环；P1 17 项按影响范围分批修复。
