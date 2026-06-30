# ALIGNMENT: 数据库架构优化

## 1. 项目上下文分析

### 1.1 项目概述

自动跟单系统是一个多组件协同的制造执行管理系统，包含以下子系统：

| 子系统 | 位置 | 核心职能 |
|--------|------|---------|
| **MySQL主系统** | `不锈钢网带跟单3.0/models/database.py` | 中央数据存储，Web管理后台 |
| **晨圣报工系统** | `backend/app.py` | 车间现场报工（Flask + SQLite） |
| **容器中心** | `mobile_api_ai/container_center_v5.py` + `storage_layer.py` | 数据中转枢纽（V5兼容） |
| **调度中心** | `mobile_api_ai/dispatch_center.py` | 企业微信机器人 + 任务分发 |
| **微信消息服务** | `mobile_api_ai/wechat_server.py` | 企业微信消息收发 |

### 1.2 当前数据库部署架构

```
                    ┌─────────────────────────────────┐
                    │       MySQL (steel_belt)         │
                    │  37+ 张表：orders, production,   │
                    │  inventory, process_records ...  │
                    │  连接池: MySQLConnectionPool     │
                    │  定时同步 ← 每5分钟/每小时       │
                    └──────────┬──────────────────────┘
                               │ 定时同步
                    ┌──────────▼──────────────────────┐
                    │  容器中心 (wechat_container.db)  │
                    │  20+ 张表：process_records(v5),  │
                    │  process_sub_steps, order_cost.. │
                    │  SQLite WAL 模式                │
                    └──────────┬──────────────────────┘
                               │ 实时同步 (EventBus + API)
                    ┌──────────▼──────────────────────┐
                    │  晨圣报工 (chengsheng.db)        │
                    │  10 张表：orders, sub_steps,     │
                    │  process_records, workers ...   │
                    │  SQLite                         │
                    └─────────────────────────────────┘

  ┌──────────────────────┐    ┌──────────────────────────┐
  │  调度中心             │    │  微信消息存储             │
  │  dispatch_center_    │    │  msg_db/YYYYMM.db        │
  │  data.json (JSON)    │    │  (按月分库)               │
  │  processes, rules... │    │  wechat_messages          │
  └──────────────────────┘    └──────────────────────────┘
```

### 1.3 关键数据流

```
晨圣报工 → (实时API) → 容器中心 → (定时5min/1h) → MySQL
  ↓                          ↑
  └── (EventBus双向同步) ────┘
  (sub_steps ↔ process_sub_steps)
```

---

## 2. 需求分析

### 2.1 原始需求

> "写个方案，整个自动跟单系统里面所有功能的数据库，看看怎样做才更利于项目的运行，现在数据库太乱了，计算同步太麻烦"

### 2.2 核心诉求拆解

| 诉求 | 具体含义 |
|------|---------|
| **数据库太乱了** | 多数据库并行、表结构不一致、字段命名混乱、数据冗余分散 |
| **计算同步太麻烦** | 跨库同步链路长（3层）、同步机制不统一、失败重试不完善、数据不一致风险高 |

### 2.3 功能域覆盖范围

本方案覆盖以下功能域的数据库设计：

1. **订单管理** — 客户订单、产品规格、BOM、工艺路线
2. **生产管理** — 工单排产、工序流转、报工记录
3. **库存管理** — 原材料入库/出库、库存盘点、物料追溯
4. **质量管理** — 质检记录、不合格品处理、质量规则
5. **完工管理** — 成品入库、发货、物流跟踪
6. **运营管理** — 操作员管理、排班、效率统计
7. **调度分发** — 任务规则、流程模板、消息模板、自动分发
8. **报修管理** — 维修类别、维修记录
9. **反馈管理** — 用户反馈
10. **容器同步** — 报工同步、数据中转
11. **微信消息** — 消息收发、会话管理

---

## 3. 当前数据库问题分析

### 3.1 P0 - 架构级问题（必须解决）

#### P0-1：多数据库并行运行，数据碎片化

当前同时运行 **5个独立数据库** + **1个JSON文件**：

| 数据库 | 类型 | 核心数据 | 问题 |
|--------|------|---------|------|
| `steel_belt` (MySQL) | 关系型 | 订单、生产、库存、质检 | 定时同步，数据滞后 |
| `chengsheng.db` | SQLite | 报工记录、工序步骤 | 字段与MySQL不一致 |
| `wechat_container.db` | SQLite | 容器V5数据、子步骤 | 与chengsheng双向同步 |
| `dispatch_center_data.json` | JSON文件 | 流程、规则、模板 | 无法查询，无事务保障 |
| `msg_db/*.db` | SQLite | 微信消息 | 按月分库，查询需跨库 |
| `scheduler_configs.db` | SQLite | 调度配置 | 少量配置数据 |

**影响**：
- 同一份数据（如订单、工序步骤）在多个数据库中冗余存储
- 数据一致性难以保证
- 同步代码维护成本高
- 排查问题需要检查多个数据源

#### P0-2：同名表在不同数据库中结构不一致

以 `orders` 表为例：

| 字段 | MySQL (steel_belt) | chengsheng.db |
|------|-------------------|---------------|
| 主键 | `id` INT AUTO_INCREMENT | `order_id` TEXT |
| 订单号 | `order_no` TEXT UNIQUE | `order_id` (兼做主键) |
| 状态 | `status` TEXT | `status` TEXT（值可能不同） |
| 客户 | 通过 `customer_id` 关联 | `name` TEXT（直接存客户名） |

以 `process_records` 表为例：

| 字段 | MySQL (steel_belt) | 容器中心 (wechat_container.db) |
|------|-------------------|-------------------------------|
| 主键 | `id` INT AUTO_INCREMENT | `id` TEXT (UUID) |
| 工单号 | `order_no` | `order_no` |
| 工序步骤 | 无 JSON 字段 | `steps TEXT` (JSON数组) |
| 效率字段 | 有 `efficiency`, `machine_no` 等 | 无 |
| 高级字段 | 无 | 有 `flow_type`, `template_id`, `task_count` |

**影响**：
- 数据迁移/同步时需做字段映射
- 同一概念在不同系统中以不同形态存在
- 查询结果不一致

#### P0-3：数据同步链路过长

```
晨圣报工 (chengsheng.db)
  → 实时API → 容器中心 (wechat_container.db)
    → 定时(5min) → EventBus双向同步
      → 定时(5min/1h) → MySQL (steel_belt)
```

- 3层同步架构，数据延迟最高可达1小时
- 同步失败后重试机制不统一
- 同步状态追踪困难
- 出现数据不一致时难以排查

#### P0-4：JSON文件替代数据库

`dispatch_center_data.json` 承担核心业务数据存储：
- `processes` — 流程实例（与数据库中的订单/工单重叠）
- `rules` — 调度规则
- `templates` — 消息模板
- `messages` — 消息记录
- `alerts` — 告警记录
- `dispatch_log` — 调度日志
- `flow_matching_rules` — 流程匹配规则

**影响**：
- 无法使用SQL查询、关联、聚合
- 无事务保障，写入可能部分失败
- 读取需全量加载，大数据量时性能差
- 无索引机制

### 3.2 P1 - 设计级问题（强烈建议解决）

#### P1-1：DAO层重复

- `d:\yuan\models\` 下有 **SQLite版本的DAO**（inventory_dao.py, production_dao.py, quality_dao.py, alert_dao.py）
- `不锈钢网带跟单3.0\models\` 下有 **MySQL版本的DAO**（order.py, production.py, process.py, etc.）
- 功能重叠但接口不一致

#### P1-2：JSON扩展字段模式

MySQL `orders.extra_params` 字段存储非固定结构数据：
```json
{
  "custom_params": {...},
  "material_params": {...},
  "weaving_params": {...}
}
```

- 无法用SQL直接查询JSON内部字段
- 类型安全无法保障
- 业务逻辑需反序列化后处理

#### P1-3：字段命名不一致

| 概念 | MySQL | chengsheng.db | 容器中心 |
|------|-------|---------------|---------|
| 订单标识 | `order_no` | `order_id` | `order_no` |
| 交期 | `delivery_date` | `delivery_date` | `delivery_date` |
| 计划时间 | `planned_start/end` | 无 | `plan_start/end` |
| 工序步骤 | `process_records` 行记录 | `sub_steps` | `process_sub_steps` |
| 数量单位 | `unit` | `unit` | `unit` |

#### P1-4：状态值硬编码为中文

```python
# 分散在代码各处的状态值
status = '待确认'   # orders
status = '生产中'   # production_orders
status = 'completed'  # 有的地方用英文
status = 'normal'     # 优先级用英文
```

- 不利于国际化
- 状态值拼写错误难以检测
- 新增状态需搜索所有引用处修改

#### P1-5：缺少审计字段和软删除

大部分表缺少：
- `created_by`, `updated_by` — 操作人追踪
- `is_deleted`, `deleted_at`, `deleted_by` — 软删除
- `version` — 乐观锁（已有部分表加了version）

### 3.3 P2 - 优化级问题（建议改进）

#### P2-1：索引策略不完善

- `_migrate_tables()` 中的 `ensure_performance_indexes()` 仅覆盖部分表
- 部分表缺少外键索引
- 未定期执行 `ANALYZE` 和 `OPTIMIZE`

#### P2-2：编号生成器分散

- `generate_order_no()` → `ORD-YYYYMMDDXXXX`
- `generate_order_no()` → `WO-YYYYMMNNN`
- `generate_shipment_no()` → `SHP-YYYYMMDDXXXX`
- 无统一的服务/接口管理编号规则

#### P2-3：SQLite 大量使用但无统一管理

- 5个 SQLite 数据库分布在项目不同目录
- 连接管理方式各不相同（有的用 `sqlite3.connect`，有的用 Flask `g`）
- 无统一的备份/恢复策略
- 无统一的迁移管理

---

## 4. 边界确认

### 4.1 方案范围

**包含**：
- 数据库表结构统一设计（覆盖所有功能域）
- 数据流架构优化（简化同步链路）
- 存储层统一方案（JSON → DB、SQLite 收敛）
- 字段命名规范、状态值规范
- 索引策略、审计策略
- 实施路线图

**不包含**：
- 业务逻辑重构（DAO 层接口设计可涉及，但不包括业务流程改造）
- UI/前端改动
- 云端部署架构（`wechat_server.py` 为云端专用，禁止修改）
- 已有数据的迁移脚本编写（仅设计方案，迁移脚本在实施阶段编写）

### 4.2 约束条件

1. **必须兼容现有运行环境**：方案实施过程中不能中断生产环境
2. **wechat_server.py 禁止修改**：云端专用文件，不在本项目中操作
3. **增量改造优先**：不要求一步到位，支持分阶段实施
4. **保持对外接口兼容**：API 层需保持向后兼容
5. **SQLite → MySQL 非强制合并**：SQLite 作为本地缓存可保留，但需统一管理

---

## 5. 疑问澄清

以下问题基于现有项目分析已做决策：

| 问题 | 决策 | 依据 |
|------|------|------|
| 是否合并所有数据库为一个？ | **不合并**。保留 MySQL 为主库、SQLite 为本地加速/离线缓存的架构，但简化同步为2层 | 车间网络不稳定，SQLite 可离线运行 |
| JSON文件是否全部迁移到DB？ | **是**。调度中心数据迁移到 SQLite 或 MySQL，JSON 仅作配置导入/导出格式 | JSON 无法查询和事务保障 |
| 是否统一字段命名风格？ | **是**。使用 `snake_case` + 英文命名，废弃中文状态值 | 行业标准，便于维护 |
| 是否统一状态值枚举？ | **是**。定义集中式枚举，代码中使用枚举常量 | 避免硬编码字符串散落各处 |
| 同步链路缩短到几层？ | **2层**：SQLite（本地）↔ MySQL（云端），去掉中间容器中心同步层 | 容器中心作为数据中转的必要性弱，可直接同步 |
| extra_params JSON 如何处理？ | **拆分为规范化字段**到关联表，保留 `extra_data` TEXT 存极少量的真正扩展数据 | 90% 的 JSON 内容已是固定结构 |

---

## 6. 验收标准

1. **方案文档覆盖所有功能域** — 订单、生产、库存、质检、完工、运营、调度、报修、反馈、消息
2. **所有数据库表结构定义完整** — 字段名/类型/约束/默认值/索引
3. **数据流架构清晰** — 同步链路不超过2层，同步机制统一
4. **ER图完整** — 表间关系明确，主外键定义完整
5. **实施路线可行** — 分阶段实施，每阶段可独立验证
6. **JSON文件数据已规划迁移路径** — 调度中心数据全部迁移到数据库
7. **字段命名规范已定义** — 统一命名规则，废弃中文状态值
8. **审计策略已定义** — 所有核心表含审计字段

---

*文档版本: v0.1*
*创建日期: 2026-05-22*
