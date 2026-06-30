# CONSENSUS: 数据库架构优化 — 技术共识

## 1. 技术方案总览

### 1.1 核心决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| **目标架构** | MySQL主库 + SQLite本地缓存（2层） | 保留离线能力，缩短同步链路 |
| **同步方式** | 统一为单向同步（SQLite → MySQL），去除容器中心中转 | 去掉EventBus双向同步，简化数据流 |
| **JSON数据** | 全部迁移到数据库表 | 获得SQL查询和事务保障 |
| **字段命名** | 统一 `snake_case` 英文命名 | 标准化，废弃中文状态值 |
| **状态枚举** | 定义 `StatusEnum` 集中管理 | 消除硬编码字符串 |
| **extra_params** | 拆为规范字段到关联表 | 可SQL查询，类型安全 |
| **DAO层** | 统一接口，MySQL版为主，SQLite版适配 | 消除重复 |

### 1.2 目标架构

```
  ┌──────────────────────────────────────────────┐
  │             MySQL (steel_belt)                │
  │  orders │ production_orders │ process_records │
  │  inventory │ quality_records │ finished_goods │
  │  customers │ operators │ dispatch_rules      │
  │  flow_templates │ messages │ alerts          │
  │  repairs │ feedback │ system_configs         │
  └────────────────────┬─────────────────────────┘
                       │ 单向同步（定时+触发）
                       │ (SQLite → MySQL)
  ┌────────────────────▼─────────────────────────┐
  │          SQLite 本地缓存层                     │
  │  ┌─────────────┐ ┌──────────────────────┐    │
  │  │ chengsheng  │ │  msg_db/             │    │
  │  │ .db (报工)  │ │ (消息存储, 按月分库) │    │
  │  └─────────────┘ └──────────────────────┘    │
  └──────────────────────────────────────────────┘
```

---

## 2. 数据流架构

### 2.1 当前（3层同步）

```
晨圣报工 ──(实时API)──→ 容器中心 ──(定时5min)──→ MySQL
                          ↑
                   (EventBus双向同步)
```

**问题**：
- 3层链路，数据延迟高
- 容器中心既存数据又中转，职责模糊
- EventBus 双向同步增加复杂度

### 2.2 目标（2层同步，单向）

```
晨圣报工 ──(定时+事件触发)──→ MySQL
  (SQLite)                    (主库)
      │
      └── 本地查询/离线操作

微信消息 ──(定时)──→ MySQL
  (SQLite)              (主库)
```

**关键变更**：
1. **去掉容器中心数据中转角色** — 晨圣报工直接同步到 MySQL
2. **EventBus 双向同步改为单向** — SQLite → MySQL 单向推送
3. **容器中心仅保留 v5 兼容 API 层** — 不存储数据，只做格式转换
4. **同步机制统一为 `SyncEngine`** — 统一的重试、状态跟踪、日志

### 2.3 同步策略

| 数据 | 同步方式 | 触发条件 | 优先级 |
|------|---------|---------|-------|
| 报工记录 (sub_steps) | 事件触发 + 定时补传 | 每次报工后立即同步；每5min定时补传 | P0 |
| 工单状态变更 | 事件触发 | 状态变化后立即同步 | P0 |
| 工序记录 | 定时同步 | 每5min | P1 |
| 员工/排班 | 定时同步 | 每30min | P2 |
| 微信消息 | 定时同步 | 每1h | P2 |
| 调度配置 | 按需同步 | 配置保存时同步 | P1 |

---

## 3. 表结构设计原则

### 3.1 统一规范

#### 主键命名
- MySQL：`id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY`
- SQLite：`id INTEGER PRIMARY KEY AUTOINCREMENT`
- 所有表统一使用 `id` 作为主键名

#### 审计字段（所有核心表）

```sql
created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
created_by    VARCHAR(64),
updated_by    VARCHAR(64),
is_deleted    TINYINT(1) DEFAULT 0,
deleted_at    DATETIME,
deleted_by    VARCHAR(64),
version       INT DEFAULT 1
```

#### 状态枚举

```python
from enum import Enum

class OrderStatus(str, Enum):
    PENDING = 'pending'           # 待确认
    CONFIRMED = 'confirmed'       # 已确认
    IN_PRODUCTION = 'in_production'  # 生产中
    COMPLETED = 'completed'       # 已完成
    CANCELLED = 'cancelled'       # 已取消

class ProcessStatus(str, Enum):
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    REJECTED = 'rejected'
    SKIPPED = 'skipped'
```

#### 字段命名规范

```
# ✅ 正确
order_no, order_no, customer_id, delivery_date, planned_qty

# ❌ 不正确（避免）
orderId, workOrderNo, CustomerName, 客户名称
```

### 3.2 JSON 扩展字段处理

```
extra_params (当前)                   规范化后
├── custom_params: {...}     →    custom_params 表 (1:N)
├── material_params: {...}   →    order_materials 表 (1:N)
├── weaving_params: {...}    →    material_rules 表 (1:1)
└── 少量真正扩展数据           →    extra_data TEXT (JSON)
```

---

## 4. 功能域表结构规划

### 4.1 表清单总览（48张表）

| 编号 | 功能域 | 表名 | 说明 |
|------|--------|------|------|
| 1-6 | **客户管理** | `customers`, `customer_contacts`, `customer_groups` | 客户及联系人 |
| 7-12 | **订单管理** | `orders`, `order_items`, `bom_list`, `material_rules`, `custom_params`, `order_templates` | 订单及规格参数 |
| 13-19 | **生产管理** | `production_orders`, `processes`, `process_records`, `process_sub_steps`, `schedule_queue`, `production_stats`, `process_calc_rules` | 工单排产报工 |
| 20-24 | **库存管理** | `inventory`, `inventory_records`, `material_history`, `material_densities`, `material_templates` | 原材料库存 |
| 25-29 | **质量管理** | `quality_records`, `quality_record_items`, `quality_rules`, `quality_rule_items`, `quality_templates` | 质检及规则 |
| 30-33 | **完工管理** | `finished_goods`, `shipments`, `shipment_tracks`, `packing_lists` | 成品发货 |
| 34-37 | **运营管理** | `operators`, `operator_logs`, `attendance_records`, `performance_stats` | 人员效率 |
| 38-40 | **调度分发** | `dispatch_rules`, `flow_templates`, `flow_matching_rules` | 规则模板 |
| 41-43 | **模板消息** | `message_templates`, `message_logs`, `notification_queue` | 消息通知 |
| 44-45 | **报修管理** | `repair_categories`, `repair_records` | 维修 |
| 46 | **反馈管理** | `feedback_records` | 反馈 |
| 47-48 | **系统配置** | `system_configs`, `audit_logs` | 配置审计 |

### 4.2 核心 ER 关系

```
customers 1──N orders 1──N production_orders 1──N process_records 1──N process_sub_steps
                  │                                       │
                  1──N order_items                    process_sub_steps 1──1 quality_records
                  │
                  1──N bom_list
                  
orders  1──N inventory_records
production_orders 1──N inventory (物料领用)

operators 1──N process_sub_steps
operators 1──N operator_logs
```

---

## 5. 技术约束

### 5.1 数据库选择

| 存储类型 | 用途 | 说明 |
|---------|------|------|
| MySQL 8.0+ | 主系统库，Web管理后台 | 中央数据存储 |
| SQLite 3.x | 本地缓存/离线库（仅 chengsheng.db + msg_db） | 车间离线操作 |
| **废弃** | 容器中心 SQLite（wechat_container.db） | 数据迁到 MySQL |
| **废弃** | JSON 文件（dispatch_center_data.json） | 数据迁到 MySQL |
| **废弃** | 独立配置库（scheduler_configs.db） | 合并到 MySQL |

### 5.2 同步约束

| 约束 | 说明 |
|------|------|
| 网络中断容忍 | SQLite 本地可完全离线运行，恢复后自动补传 |
| 冲突策略 | 以 MySQL 数据为准，本地同步时检查 version 字段 |
| 最大延迟 | 定时同步 ≤ 5分钟，事件触发同步 ≤ 10秒 |
| 重试策略 | 指数退避，最多重试5次，失败记入 sync_error_log |

### 5.3 兼容性

- MySQL 表变更必须通过 `_migrate_tables()` 迁移函数（已存在模式）
- SQLite 表变更通过版本号控制（`_schema_version` 表）
- API 接口保持向后兼容（使用适配器模式包装旧接口）

### 5.4 chengsheng.db 按月归档备份

| 项目 | 说明 |
|------|------|
| **机制** | 每月首次启动时，自动将 `chengsheng.db` 复制为 `chengsheng_YYYY_MM.db` 归档快照 |
| **参考模式** | 沿用 `msg_db` 按月分库的命名规范（`wechat_messages_2026_05.db`） |
| **实现位置** | `backend/app.py` 的 `monthly_archive_backup()`，在 `init_db()` 之前执行 |
| **归档目录** | `backend/data/`（与活跃的 `chengsheng.db` 同目录） |
| **保留策略** | 保留最近 12 个月的归档，按需手动清理更早的归档 |
| **与 startup_check.py 的关系** | `startup_check.py` 按时间戳做启动前备份（`backups/` 目录）；月归档是长期快照（`data/` 目录），两者互补 |

---

## 6. 集成方案

### 6.1 实施顺序

```
Phase 1: 数据建模（本周）
  ├── 定义所有表结构 (48张表)
  ├── 定义枚举、规范文档
  └── 生成 ER 图

Phase 2: 调度中心 JSON → DB（第2周）
  ├── 创建 dispatch_rules, flow_templates 等表
  ├── 修改 dispatch_center.py 读写 DB
  └── 编写 JSON → DB 迁移脚本

Phase 3: 容器中心数据迁移到 MySQL（第3周）
  ├── process_sub_steps 等数据迁入 MySQL
  ├── 容器中心改为纯 API 代理
  └── 同步适配器改造

Phase 4: 同步链路重构（第4周）
  ├── 实现 SyncEngine 统一同步
  ├── 替换 EventBus 双向同步
  └── 废弃 wechat_container.db

Phase 5: 字段标准化（第5-6周）
  ├── 字段重命名
  ├── 状态值迁移（中文→英文枚举）
  ├── extra_params 拆分
  └── 审计字段补充

Phase 6: 测试 & 收尾（第7周）
  ├── 数据一致性验证
  ├── 性能测试
  └── 文档更新
```

### 6.2 风险控制

| 风险 | 应对 |
|------|------|
| 数据迁移丢失 | 每阶段迁移前做全量备份，迁移后做数据校验 |
| 同步中断 | 同步队列持久化到 SQLite，恢复后自动续传 |
| 字段重命名影响旧代码 | 使用 DB 视图 + 代码适配器过渡 |
| 中文状态值变更影响历史数据 | 新数据用英文枚举，历史数据用视图转换 |

---

## 7. 验收标准

1. ✅ 方案文档覆盖全部 11 个功能域
2. ✅ 48 张表结构定义完整，含字段名、类型、约束、索引
3. ✅ ER 图覆盖所有核心表间关系
4. ✅ 同步链路从 3 层缩短为 2 层
5. ✅ JSON 文件数据全部迁移到数据库
6. ✅ 统一字段命名规范（snake_case + 英文）
7. ✅ 统一状态枚举定义
8. ✅ 审计字段覆盖所有核心表
9. ✅ extra_params 拆分方案明确
10. ✅ DAO 层合并方案明确
11. ✅ 实施路线分阶段可执行

---

*文档版本: v0.1*
*创建日期: 2026-05-22*
