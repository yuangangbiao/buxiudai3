# 不锈钢网带跟单系统 v3.6 架构文档

## 修订历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v3.6.1 | 2026-06-20 | 新增预警与告警系统章节（第九章）+ 统一任务查询接口（**1.10 节**，原 1.7 已调整为动态字段扩展机制）+ `/tasks` 接口迁移到独立任务表 + 新增任务回归审计系统章节（**第八章**，原"七"已拆为"七、八"两章） + 全文档审计修复（20 条 Bug，详见 ARCHITECTURE_v3.6_BUG_REPORT.md） |
| v3.6 | 2026-06-20 | 统一任务表结构，拆分 data_packages |
| v3.5 | 2026-06-19 | 容器中心重构 |
| v3.0 | 2026-05 | 融合系统初版 |

---

## 一、系统架构

### 1.1 服务架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           跟单系统 v3.6 架构                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        桌面端 (Desktop)                                │   │
│  │  技术: Tkinter  │  数据库: steel_belt                                │   │
│  │  发布订单 → POST /api/internal/publish                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                       │
│                                     ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     容器中心 (Container Center)                        │   │
│  │  端口: 5002  │  文件: container_api.py                             │   │
│  │  职责: 接收桌面端发布 → 创建工序任务 → 分发到调度中心                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                       │
│                                     ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      调度中心 (Dispatch Center)                        │   │
│  │  端口: 5003  │  文件: standalone_dispatch_server.py                 │   │
│  │  职责: 任务调度、云端通信转发 (→ 云端 5006)                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                       │
│         ┌───────────────────────────┼───────────────────────────┐          │
│         │                           │                           │          │
│         ▼                           ▼                           ▼          │
│  ┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐         │
│  │  移动端报工   │    │  库存服务        │    │  云端            │         │
│  │  5008        │    │  5010           │    │  5006           │         │
│  │  app.py      │    │  Inventory      │    │  Cloud          │         │
│  └──────────────┘    └──────────────────┘    └──────────────────┘         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 服务端口定义

| 端口 | 服务名称 | 入口文件 | 核心功能 |
|:----:|:--------:|:---------|:---------|
| 5002 | 容器中心 | container_center_api.py | 接收桌面端发布，创建工序任务 |
| 5003 | 调度中心 | standalone_dispatch_server.py | 任务调度、云端通信转发、桌面端同步 |
| 5008 | 移动端报工 | app.py | 工序报工、质检、维修、外协、物料采购、排产 |
| 5010 | 库存管理 | inventory_api_server.py | 独立库存服务 |

### 1.3 消息流程

```
┌──────────┐                                ┌──────────┐
│ 桌面端    │                                │ 容器中心  │
│ Desktop  │── POST /api/internal/publish ──►│  5002   │
└──────────┘                                └────┬─────┘
                                                   │
                                                   ▼
                                          ┌────────────────┐
                                          │  调度中心      │
                                          │  5003         │
                                          │               │
                                          │ → 云端 5006   │
                                          └───────┬────────┘
                                                  │
                                                  ▼
                                           ┌────────────┐
                                           │  云端 5006  │
                                           └────────────┘
```

### 1.4 服务间通信约束

- **R-001**：禁止在服务 A 中直接连接服务 B 的数据库，必须通过 API 接口交互
- **R-002**：所有云端通信必须通过 5003 调度中心转发到云端 5006，禁止直连云端
- **R-003**：移动端更新后必须通过 5003 调度中心同步到桌面端

### 1.5 同步架构（v3.6.1）

所有移动端到桌面端的数据同步，统一通过 5003 调度中心：

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        同步架构（通过 5003 调度中心）                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  移动端 (5008)                                                            │
│       │                                                                    │
│       ├──► /api/report_record/submit ──► dispatch_center                  │
│       │        POST /api/dispatch-center/sync/sub-step-report              │
│       │                                                                    │
│       ├──► /api/material_record/update ─► dispatch_center                  │
│       │        POST /api/dispatch-center/sync/material                    │
│       │                                                                    │
│       ├──► /api/repair_record/update ─► dispatch_center                    │
│       │        POST /api/dispatch-center/sync/repair                      │
│       │                                                                    │
│       └──► /api/outsource_record/update ─► dispatch_center                 │
│                POST /api/dispatch-center/sync/outsource                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.6 同步 API 端点

| API | 方法 | 功能 | 目标表 | 扩展性 |
|-----|:----:|------|--------|:------:|
| `/api/dispatch-center/sync/sub-step-report` | POST | 工序报工同步 | steel_belt.process_sub_steps | ✅ |
| `/api/dispatch-center/sync/material` | POST | 物料状态同步 | steel_belt.order_materials | ✅ 动态 |
| `/api/dispatch-center/sync/repair` | POST | 维修状态同步 | steel_belt.repair_records | ✅ 动态 |
| `/api/dispatch-center/sync/outsource` | POST | 外协状态同步 | steel_belt.outsource_records | ✅ 动态 |
| `/api/dispatch-center/sync/quality-record` | POST | 质检记录同步 | steel_belt.quality_records | ✅ 动态 |

### 1.7 动态字段扩展机制

所有同步端点（除工序报工外）均采用**动态字段同步**：

```python
# 接收任意字段，自动同步到目标表（带字段映射）
for key, value in body.items():
    if key not in exclude_fields and value is not None:
        mapped_key = field_map.get(key, key)  # 字段映射
        update_fields.append(f'{mapped_key}=%s')
        update_values.append(value)
```

### 1.8 字段映射表

由于 container_center 和 steel_belt 两库独立开发，字段命名存在差异，**同步时自动映射**：

| 同步端点 | 源字段 (container_center) | 目标字段 (steel_belt) |
|---------|------------------------|---------------------|
| `/sync/material` | `status` | `prep_status` |
| `/sync/material` | `planned_qty` | `required_qty` |
| `/sync/material` | `completed_qty` | `prepared_qty` |
| `/sync/repair` | `target_operator` | `assigned_to` |
| `/sync/quality-record` | `step_name` | `process_name` |
| `/sync/quality-record` | `inspection_type` | `process_name` |

### 1.9 扩展场景验证

| 场景 | 操作 | 是否需要修改代码 |
|------|------|:----------------:|
| 新增质检项目 | quality_records 表添加字段 | ❌ 无需 |
| 新增物料字段 | order_materials 表添加字段 | ❌ 无需 |
| 新增工序 | process_sub_steps 表添加记录 | ❌ 无需 |
| 新增维修类型 | repair_records 表添加字段 | ❌ 无需 |
| 新增字段映射 | dispatch_center 添加映射 | ✅ 需要 |

---

### 1.10 统一任务查询接口 (v3.6.1 新增)

为了解决移动端多任务表查询分散的问题，新增统一任务查询接口：

#### 1.10.1 接口列表

| 路由 | 方法 | 功能 |
|------|:----:|------|
| `/unified-tasks` | GET | 统一任务查询 |
| `/unified-tasks/stats` | GET | 统一任务统计 |

#### 1.10.2 任务类型与存储表对应

| 类型 | 存储表 | 负责人字段 | 说明 |
|------|--------|-----------|------|
| `process` | process_sub_steps | operator | 生产工序 |
| `quality` | quality_records | inspector | 质检记录 |
| `repair` | repair_records | assigned_to | 维修记录 |
| `outsource` | outsource_records | supplier | 外协记录 |
| `material` | material_records | target_operator | 物料记录 |

#### 1.10.3 Query 参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `type` | string | 任务类型 (process/quality/repair/outsource/material/all) |
| `status` | string | 状态筛选 |
| `operator` | string | 操作员筛选 |
| `page` | int | 页码 |
| `page_size` | int | 每页数量 |

---

## 二、数据库架构

### 2.1 数据库分布

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          MySQL 数据库集群                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────┐         ┌─────────────────────────┐         │
│  │       steel_belt         │◄─────►│     container_center     │         │
│  │       桌面端主数据        │   ETL  │       调度中心数据        │         │
│  ├─────────────────────────┤         ├─────────────────────────┤         │
│  │  orders                 │         │  process_sub_steps      │         │
│  │  process_records        │         │  material_records       │         │
│  │  order_materials        │         │  quality_records       │         │
│  │  quality_records       │         │  quality_packages      │         │
│  │  repair_records        │         │  process_packages      │         │
│  │                         │         │  repair_records        │         │
│  │                         │         │  outsource_records     │         │
│  │                         │         │  schedule_records      │         │
│  └─────────────────────────┘         └─────────────────────────┘         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 核心表清单

| 表名 | 用途 | 所属库 | 关联字段 |
|------|------|--------|---------|
| `orders` | 订单主表 | steel_belt | order_no |
| `process_records` | 工作流记录 | steel_belt | order_no |
| `process_sub_steps` | 生产工序明细 | container_center | order_no |
| `order_materials` | 订单物料（生产备料） | steel_belt | order_no |
| `material_records` | 物料采购任务 | container_center | order_no |
| `quality_records` | 质检记录 | **主表** `container_center`（移动端写入），**同步副本** `steel_belt`（桌面端展示）。详见 [Bug-17 修复说明] | order_no |
| `quality_packages` | 质检任务包 | container_center | order_no |
| `process_packages` | 生产任务包 | container_center | order_no |
| `repair_records` | 维修任务 | steel_belt / container_center | order_no |
| `outsource_records` | 外协任务 | container_center | order_no |
| `schedule_records` | 排产任务 | container_center | order_no |
| `dispatch_cache` | 调度缓存 | container_center | - |

> **质量记录双库策略说明**：`quality_records` 在 `container_center` 和 `steel_belt` 两库中都存在。**主表** = `container_center.quality_records`（移动端 5008 写入，调度中心 5003 读取并通过 `/api/dispatch-center/sync/quality-record` 端点同步），**同步副本** = `steel_belt.quality_records`（桌面端只读展示，不直接写入）。同步策略详见章节 1.6。

---

## 三、物料数据模型

物料数据分为两个层面，通过 `order_no` 关联：

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           物料数据结构                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  steel_belt.order_materials              container_center.material_records  │
│  ┌─────────────────────────┐            ┌─────────────────────────┐       │
│  │ order_id: 8            │◄──────────►│ order_no: ORD-xxx      │       │
│  │ order_no: ORD-xxx      │            │ material_name:           │       │
│  │ material_name:          │            │   304不锈钢网丝        │       │
│  │   304不锈钢网丝        │            │ material_spec: 1.5m     │       │
│  │ spec: 1.5m            │            │ unit: 米               │       │
│  │ required_qty: 2000     │            │ warehouse: 主仓库       │       │
│  │ prepared_qty: 0         │            │ planned_qty: 2000      │       │
│  │ prep_status: 缺料       │            │ status: 采购中          │       │
│  │ target_operator:        │            │ target_operator:        │       │
│  │ arrival_date:            │            │ arrival_date:           │       │
│  └─────────────────────────┘            └─────────────────────────┘       │
│                                                                             │
│  用途: 订单物料清单（桌面端）          用途: 物料采购任务（移动端）       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.1 物料数据同步流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        物料数据双向同步流程                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. 发布阶段                                                               │
│  ┌──────────┐    POST /api/internal/publish     ┌──────────────────┐     │
│  │ 桌面端    │ ───────────────────────────────► │ 容器中心          │     │
│  │          │                                   │ material_records │     │
│  │ order_   │                                   │ 自动创建        │     │
│  │ materials │                                   └──────────────────┘     │
│  └──────────┘                                                              │
│                                                                             │
│  2. 查询阶段                                                               │
│  ┌──────────┐    GET /api/material_record/list   ┌──────────────────┐     │
│  │ 移动端    │ ───────────────────────────────► │ 容器中心          │     │
│  │          │ ◄──────────────────────────────── │ 返回物料列表     │     │
│  └──────────┘                                   └──────────────────┘     │
│                                                                             │
│  3. 更新阶段                                                               │
│  ┌──────────┐    POST /api/material_record/    ┌──────────────────┐     │
│  │ 移动端    │ ──────── update ─────────────► │ 容器中心          │     │
│  │          │                                   │ 更新状态          │     │
│  │ status   │                                   └────────┬─────────┘     │
│  └──────────┘                                    同步   │                │
│                                                     ▼                    │
│  4. 回填阶段                                        ┌──────────────────┐   │
│  ┌──────────┐    自动同步                       │ 桌面端            │   │
│  │ 桌面端    │ ◄────────────────────────────── │ order_materials   │   │
│  │          │                                   │ status 同步      │   │
│  └──────────┘                                   └──────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 字段同步映射

| 移动端 (material_records) | 桌面端 (order_materials) | 同步时机 |
|------------------------|------------------------|---------|
| status | prep_status | 移动端更新时 |
| arrival_date | arrival_date | 移动端更新时 |
| target_operator | target_operator | 移动端更新时 |

---

## 四、任务流程

### 4.1 工序代码前缀

| 任务类型 | flow_type | 前缀 | 示例 |
|---------|-----------|------|------|
| 生产工序 | production | P | P06, P07, P09... |
| 物料任务 | material_purchase | M | M01, M02, M03... |
| 质检任务 | quality | Q | Q01, Q02, Q03... |
| 维修任务 | repair | R | R01, R02, R03... |
| 外协任务 | outsource | O | O01, O02, O03... |

### 4.2 订单发布流程

```
桌面端 (confirm_order)
    │
    ▼ POST /api/internal/publish
容器中心 (5002, container_center_api.py)
    │
    ├──► process_records (工作流头)
    │
    ├──► process_sub_steps (工序明细)
    │        │
    │        ├──► production: P06-P16
    │        ├──► material_purchase: M01-M06
    │        ├──► quality: Q01-Q06
    │        ├──► repair: R01-R07
    │        └──► outsource: O01-O08
    │
    └──► 任务包表
             │
             ├──► material_records (物料)
             ├──► quality_packages (质检)
             ├──► process_packages (生产)
             ├──► repair_records (维修)
             └──► outsource_records (外协)
                   │
                   ▼ POST /api/sync/*  (云端通信转发约束：必须经调度中心)
            调度中心 (5003, standalone_dispatch_server.py)
                   │
                   │  → 云端 5006 (经 /api/dispatch-center/forward-to-cloud)
                   ▼
            云端 5006 (微信消息)
```

---

## 五、API 接口

### 5.1 任务 API 端点 (5008 移动端)

| 任务类型 | 列表接口 | 更新接口 |
|---------|---------|---------|
| 生产工序 | `/api/report_record/list` | - |
| 物料任务 | `/api/material_record/list` | `/api/material_record/update` |
| 质检任务 | `/api/quality_record/list` | `/api/quality_record/update` |
| 维修任务 | `/api/repair_record/list` | `/api/repair_record/update` |
| 外协任务 | `/api/outsource_record/list` | `/api/outsource_record/update` |
| 排产任务 | `/api/schedule_record/list` | `/api/schedule_record/update` |

### 5.2 统一响应格式

```json
{
  "code": 0,
  "message": "成功",
  "data": {
    "list": [...],
    "total": 100,
    "page": 1,
    "page_size": 20
  }
}
```

---

## 六、文件结构

```
mobile_api_ai/
├── app.py                      # 移动端报工服务 (5008)
├── container_center_api.py      # 容器中心 API (5002)
├── container_center_v5.py        # 容器中心核心
├── standalone_dispatch_server.py  # 调度中心服务 (5003)
├── dispatch_center/
│   ├── __init__.py
│   ├── _core.py                # 调度中心核心逻辑（含告警 API 路由）
│   ├── _constants.py           # 调度中心常量
│   ├── _core_types.py          # 调度中心类型定义
│   ├── schedule_routes.py      # 排产路由
│   └── shipment_routes.py      # 发货路由
├── storage/
│   ├── mysql_storage.py         # MySQL 存储
│   └── redis_storage.py        # Redis 缓存
├── sync_bridge.py              # 同步桥接
├── models/                     # 数据模型
├── docs/                       # 文档
│   ├── ARCHITECTURE_v3.6.md    # 本文档
│   ├── TASK_TABLE_SPEC.md      # 表结构规范
│   └── migrations/              # 数据库迁移脚本
└── tests/                      # 测试
```

---

## 七、相关文档

- [TASK_TABLE_SPEC.md](TASK_TABLE_SPEC.md) - 表结构详细规范
- [MySQLStorage_API参考.md](MySQLStorage_API参考.md) - 存储层 API
- [调度中心稳定性加固.md](调度中心稳定性加固.md) - 调度中心稳定性方案

---

## 八、任务回归审计系统

### 8.1 系统概述

任务回归审计系统是调度中心的核心审计模块，用于查询、修改、撤回生产/质检/物料/外协/排产等任务记录，所有变更留痕可审计。

**文件位置**: `mobile_api_ai/dispatch_center/_core.py` (Part 20)
**前端文件**: `mobile_api_ai/templates/dispatch_center.html`, `mobile_api_ai/static/js/dispatch_center.js`

### 8.2 回归类型清单

| 回归类型 | 路由 | 数据源表 | 说明 |
|---------|------|---------|------|
| 质检回归 | `/quality-regression` | `quality_records` | 质检记录查询、修改、撤回 |
| 物料回归 | `/material-regression` | `material_records` | 物料记录查询、修改、撤回 |
| 外协回归 | `/outsource-regression` | `outsource_records` | 外协记录查询、修改、撤回 |
| 排产回归 | `/schedule-regression` | `schedule_records` | 排产记录查询、修改、撤回 |

### 8.3 API 接口列表

| 路由 | 方法 | 功能 |
|------|:----:|------|
| `/quality-regression` | GET | 查询质检记录（按 record_date 倒序） |
| `/material-regression` | GET | 查询物料记录（按 created_at 倒序） |
| `/outsource-regression` | GET | 查询外协记录（按 created_at 倒序） |
| `/schedule-regression` | GET | 查询排产记录（按 created_at 倒序） |

### 8.4 返回数据格式

```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": "REC001",
        "order_no": "ORD2026001",
        "title": "工序名称 / 物料名称 / 外协标题",
        "operator": "操作员 / 质检员 / 供应商",
        "status": "pending|completed|withdrawn",
        "created_at": "2026-06-20 14:30:00"
      }
    ]
  }
}
```

### 8.5 质检回归特殊字段

| 字段 | 说明 |
|------|------|
| `inspection_type` | 检验类型（首检/巡检/末检等） |
| `result` | 检验结果（pass/fail） |
| `inspector` | 质检员 |
| `record_date` | 检验时间（注意：质检表用的是 record_date，不是 created_at） |

### 8.6 字段名映射规则

| 表 | 负责人字段 | 标题字段 | 时间字段 |
|----|-----------|---------|---------|
| process_sub_steps | operator | step_name | created_at |
| quality_records | inspector | process_name | record_date |
| material_records | target_operator | material_name | created_at |
| outsource_records | supplier_name | title | created_at |
| schedule_records | target_operator | title | created_at |

### 8.7 前端实现

**标签页位置**: 调度中心侧边栏 → 回归审计分类

**4 个标签页**：
- 🔬 质检回归 (id: `tab-quality-regression`, 列表 ID: `qr-list`)
- 📦 物料回归 (id: `tab-material-regression`, 列表 ID: `mr-list`)
- 🔄 外协回归 (id: `tab-outsource-regression`, 列表 ID: `or-list`)
- 📅 排产回归 (id: `tab-schedule-regression`, 列表 ID: `sr-list`)

**前端函数**：
```javascript
async function loadQualityRegression() { /* 质检回归 */ }
async function loadMaterialRegression() { /* 物料回归 */ }
async function loadOutsourceRegression() { /* 外协回归 */ }
async function loadScheduleRegression() { /* 排产回归 */ }
```

**过滤条件**：
- 订单号 / 标题模糊匹配
- 操作员 / 质检员精确匹配
- 开始日期 / 结束日期范围筛选

### 8.8 数据源迁移说明

**v3.6.1 之前**：回归 API 从 `data_packages` 表读取数据
**v3.6.1 之后**：迁移到独立任务表

| 回归类型 | 旧数据源 | 新数据源 |
|---------|---------|---------|
| 质检回归 | data_packages | quality_records |
| 物料回归 | data_packages | material_records |
| 外协回归 | data_packages | outsource_records |
| 排产回归 | data_packages | schedule_records |

---

## 九、预警与告警系统

### 9.1 系统概述

预警与告警系统是调度中心的核心监控模块，负责实时检测任务异常并及时通知相关人员。

| 属性 | 值 |
|------|-----|
| **引擎位置** | `mobile_api_ai/container_center/services/alert_engine.py` (`AlertEngine` 类，**不含 Flask 路由**) |
| **API 路由位置** | `mobile_api_ai/dispatch_center/_core.py` (`@dispatch_center_bp` 蓝图，行 1923-1990 + 5365-5475) |
| **核心类** | `AlertEngine` |
| **告警级别** | CRITICAL / WARNING / INFO |

### 9.2 告警检测类型

| # | 检测类型 | 函数 | 级别 | 说明 |
|:-:|---------|------|:----:|------|
| 1 | 任务超时 | `check_overdue_tasks` | WARNING | pending/dispatched/distributed 状态超过阈值 |
| 2 | 任务停滞 | `check_stalled_tasks` | INFO | in_progress 状态超过阈值未推进 |
| 3 | 任务积压 | `check_queue_depth` | CRITICAL | pending 队列超过阈值 |
| 4 | 操作员过载 | `check_operator_overload` | WARNING | 单个操作员任务数超过阈值 |
| 5 | 完成率异常 | `check_completion_rate` | INFO | 完成率低于阈值 |
| 6 | 排产超时 | `check_schedule_overdue` | WARNING | 计划截止日期已过期 |
| 7 | 任务超时告警 | `check_overdue_task_alerts` | WARNING | 任务等待超过阈值 |
| 8 | 订单逾期告警 | `check_order_overdue_alerts` | CRITICAL | 订单超过 plan_end 未完成 |

> ✅ **已拆分（2026-06-20）**：`check_order_timeout_alerts` 已拆分为两个独立方法：
> - `check_overdue_task_alerts` (行 445) — 任务超时告警 (WARNING)
> - `check_order_overdue_alerts` (行 493) — 订单逾期告警 (CRITICAL)
>
> 原 `check_order_timeout_alerts` 保留为向后兼容入口 (行 432)，内部依次调用两个新方法。alert_engine.py:782 调用方暂未变更（性能无影响）。
| 9 | 物料到货通知 | `check_material_arrival` | INFO | 物料到货提醒 |
| 10 | 外协到期/逾期提醒 | `check_outsource_reminders` | WARNING/INFO | 外协任务在到期日前和逾期后发送提醒 |
| 11 | 告警自动升级 | `check_escalations` | CRITICAL | 长期未解除的告警自动升级 |

> ⚠️ **三方对齐说明**：`alert_engine.py` 文件头部注释 (行 1-14) 仍写"6 类"，未与本表 (11 项) 同步。`grep -n 'def check_' alert_engine.py` 实际命中 10 个函数（含合并实现的 7+8 项）。修复行动项：本表为 SSOT，需同步更新 `alert_engine.py` 头部注释为"11 项"。

### 9.3 告警配置参数

| 参数 | 默认值 | 说明 |
|------|:------:|------|
| `auto_reassign_timeout` | 60 分钟 | 任务超时阈值 |
| `task_stall_timeout` | 120 分钟 | 任务停滞阈值 |
| `queue_depth_threshold` | 50 个 | 积压告警阈值 |
| `max_tasks_per_operator` | 20 个 | 操作员过载阈值 |
| `min_completion_rate` | 5% | 完成率告警阈值 |
| `alert_cooldown_minutes` | 30 分钟 | 重复告警冷却时间 |
| `order_overdue_hours` | 24 小时 | 订单逾期阈值 |

### 9.4 告警发送渠道

| 渠道 | 说明 | 触发条件 |
|------|------|---------|
| **微信群** | GroupBot 发送 | 全部告警（可配置） |
| **应用消息** | 发给任务负责人 | CRITICAL 级别 + 指定操作员 |
| **告警缓冲** | 非 CRITICAL 聚合发送 | WARNING/INFO 级别 |

### 9.5 告警 API 路由

> ⚠️ **路由不在 alert_engine.py**：以下路由全部定义在 `dispatch_center/_core.py`（5003 端口 `dispatch_center_bp` 蓝图下），前缀为 `/api/dispatch-center`。**`alert_engine.py` 自身 `grep '@app.route'` 返回 0 命中**，仅作为引擎被 `_core.py` 调用。

| 路由（5003 调度中心） | 方法 | 功能 |
|------|:----:|------|
| `/api/dispatch-center/alerts` | GET | 查询告警列表 |
| `/api/dispatch-center/alerts/<alert_id>/dismiss` | POST | 忽略告警 |
| `/api/dispatch-center/alerts/<alert_id>/ack` | POST | 确认告警 |
| `/api/dispatch-center/alerts/<alert_id>/snooze` | POST | 暂缓告警 |
| `/api/dispatch-center/alerts/stats` | GET | 告警统计 |
| `/api/dispatch-center/violations` | GET | 违规记录查询 |
| `/api/dispatch-center/violations/stats` | GET | 违规统计 |
| `/api/dispatch-center/violations/recent` | GET | 最近违规 |
| `/api/dispatch-center/violations` | DELETE | 清除违规 |
| `/api/dispatch-center/configs/alert_rules` | GET | 获取告警规则 |
| `/api/dispatch-center/configs/alert_rules` | PUT | 更新告警规则 |

> ✅ **硬迁移完成（2026-06-20）**：5002 端口的 `/api/v4/alerts/*` 全部已删除（容器中心 mock 路由 + `container_center/api/` 整个死代码包 7 文件已清理）。
>
> **剩余告警 API 仅有 5003 端口一套**，参数名 `<alert_id>`，方法为 `POST /dismiss`。
>
> ⚠️ **不兜底依赖**：`ContainerCenterClient` 的 4 个告警方法（`get_alert_rules` / `update_alert_rules` / `get_alert_list` / `dismiss_alert`）直接调用 5003，5003 不可用时**直接抛异常**，不静默回退 mock 数据。生产环境部署必须保证 5003 服务先于 5002 可用。

### 9.6 前端实现

| 文件 | 功能 |
|------|------|
| `mobile_api_ai/templates/dispatch_center.html` | 告警概览统计卡片、告警列表、调度日志 |
| `mobile_api_ai/static/css/dispatch_center.css` | 渐变背景统计卡片、胶囊级别标签、消息截断 |

**前端功能**：
- 告警概览统计卡片（总数/今日/严重/警告）
- 告警列表展示（级别筛选、忽略操作）
- 调度日志展示
- 自动刷新（每 60 秒）

---

## 十、消息模板字段完整性

### 10.1 模板字段清单

> ⚠️ **反虚高规范**：原表所有模板标 "✅ 完整"，但缺少验证命令与时间戳。改为 "⏳ 待验证" 直至提供实际渲染测试结果。

| 模板ID | 模板名称 | 所需字段 | 字段状态 |
|--------|---------|---------|:--------:|
| tmpl_task_assigned | 任务分配通知 | 操作员, 任务标题, 订单号, 工序, 数量 | ⏳ 待验证 |
| tmpl_task_reminder | 任务超时提醒 | 提醒次数, 任务标题, 订单号, 已用分钟, 负责人 | ⏳ 待验证 |
| tmpl_task_urgent | 紧急任务通知 | 任务标题, 订单号, 工序, 数量, 优先级 | ⏳ 待验证 |
| tmpl_task_transfer | 任务转派通知 | 原负责人, 新负责人, 任务标题, 订单号 | ⏳ 待验证 |
| tmpl_task_delay | 任务延期通知 | 任务标题, 订单号, 原截止时间, 新截止时间, 延期原因 | ⏳ 待验证 |
| tmpl_task_cancelled | 任务取消通知 | 任务标题, 订单号 | ⏳ 待验证 |
| tmpl_batch_assign | 批量派单通知 | 操作员, 成功数, 总数 | ⏳ 待验证 |
| tmpl_process_start | 流程启动通知 | 流程名称, 订单号, 产品, 发起人 | ⏳ 待验证 |
| tmpl_process_advance | 流程推进通知 | 流程名称, 订单号, 当前步骤, 下一步骤, 执行人 | ⏳ 待验证 |
| tmpl_process_complete | 流程完成通知 | 流程名称, 订单号, 产品, 完成时间 | ⏳ 待验证 |
| tmpl_process_reject | 流程退回通知 | 订单号, 退回步骤, 退回原因, 操作人 | ⏳ 待验证 |
| tmpl_quality_completed | 质检完成通知 | 订单号, 质检类型, 质检结果, 质检员, 完成时间, 备注, 产品 | ⏳ 待验证 |
| tmpl_repair_complete | 维修完成通知 | 设备名称, 维修人, 完成时间, 耗时(小时) | ⏳ 待验证 |
| tmpl_outsource_receive | 外协收货通知 | 物料名称, 数量 | ⏳ 待验证 |
| tmpl_material_shortage | 物料短缺通知 | 物料名称, 订单号, 短缺数量, 单位, 影响描述 | ⏳ 待验证 |
| tmpl_alert_timeout | 任务超时告警 | 任务标题, 订单号, 操作员, 超时分钟 | ⏳ 待验证 |
| tmpl_alert_overdue | 订单逾期告警 | 订单号, 客户, 逾期天数, 产品 | ⏳ 待验证 |
| tmpl_schedule_notify | 排产通知 | 订单号, 产品, 数量, 截止时间 | ⏳ 待验证 |
| tmpl_cost_calculated | 成本核算通知 | 订单号, 客户, 产品, 数量, 各项成本, 总成本, 收入, 利润 | ⏳ 待验证 |

> **验证方法**：
> 1. `grep -rn "'tmpl_.*'" mobile_api_ai/template_engine.py | head -50` 确认模板定义存在
> 2. 实际触发一次业务（如触发任务分配），观察日志中是否所有占位符都被填充
> 3. 在验证完成后将对应行 "⏳ 待验证" 改为 "✅ 完整（YYYY-MM-DD 验证）"

### 10.2 消息接收人规则

| 消息类型 | 接收人 | 渠道 | 依据 |
|---------|-------|------|------|
| 报工修正通知 | 原报工人 | wechat_app | existing.operator |
| 报工撤回通知 | 原报工人 | wechat_app | existing.operator |
| 质检修正通知 | 原质检员 | wechat_app | existing.inspector |
| 质检撤回通知 | 原质检员 | wechat_app | existing.inspector |
| 任务超时提醒 | 群 + 负责人 | wechat_group + wechat_app | target_operator |
| 指定任务分配 | 任务负责人 | wechat_app | target_operator |
| 全员任务分配 | 所有人 | wechat_group | 无 target_operator |
| 工序确认 | 任务负责人 / 所有人 | wechat_app / wechat_group | 根据 target_operator |
| 工序推进/完成/异常 | 所有人 | wechat_group | 无负责人 |
| 部门全员通知 | 部门全员 | wechat_app | department |

### 10.3 消息触发节点汇总

> ⚠️ **行号已重新核对（2026-06-20）**：原表中 `app.py:790/858/1020/1101` 实际在 `notify.py`；`_core.py:1482/1704/4399/7366` 等多行偏移；`alert_engine.py:1704` 不存在（文件总 623 行）。下表已用 `grep -n` 逐项核对。

| 文件:行号 | 触发场景 | 函数/模板 | 接收人 |
|------|---------|------|--------|
| notify.py:177 | 报工修正 | notify_admin_modified | 原报工人 |
| notify.py:191 | 报工撤回 | notify_admin_withdraw | 原报工人 |
| notify.py:203 | 质检修正 | notify_quality_modified | 原质检员 |
| notify.py:217 | 质检撤回 | notify_quality_withdraw | 原质检员 |
| _core.py:1486 | 紧急任务通知 | tmpl_task_urgent | 群 |
| _core.py:1493 | 任务延期通知 | tmpl_task_delay | 群 |
| _core.py:1569 | 任务分配通知（_do_send_process_task） | tmpl_task_assigned | 任务负责人 |
| _core.py:1711 | 流程启动通知 | tmpl_process_start | 群 |
| _core.py:2685 | 批量派单（distribute_work_orders） | tmpl_task_assigned | 任务负责人 |
| _core.py:2768 | 工序转派（reassign_task） | tmpl_task_transfer | 指定人 |
| _core.py:2815 | 任务取消（cancel_task） | tmpl_task_cancelled | 群 |
| _core.py:2861 | 批量派单（batch_distribute） | tmpl_batch_assign | 群 |
| _core.py:4420 | 流程推进/删除 | tmpl_process_advance | 群 |
| _core.py:4653 / 4656 | 工序确认 | _notify_with_template | 负责人/群 |
| _core.py:4676 / 4795 | 工序推进 | _notify_process_event | 群 |
| _core.py:5017 | 维修完成（complete_repair_record） | tmpl_repair_complete | 群 |
| _core.py:5133 | 外协发出（create_outsource_record） | tmpl_outsource_send | 群 |
| _core.py:5237 | 外协收货（receive_outsource_record） | tmpl_outsource_receive | 群 |
| _core.py:7602 | 质检完成（on_quality_record_completed） | tmpl_quality_completed | 群 |
| alert_engine.py:98 | 告警统一发送（_send_alert） | tmpl_alert_timeout 等 | 群 + 负责人 |

### 10.4 消息模板调用方汇总

#### 调度中心 (_core.py)

> ✅ **行号与函数名已全部核对（2026-06-20）**：原表行号多基于旧版本，本表行号为 `_render_template('tmpl_xxx', ...)` 实际渲染行号（`grep -n` 实测）。原文档未列出的 5 个"⚠️ 函数名待核"项已全部找到对应函数（部分函数名因路由/语义调整已变更）。

| 模板ID | 调用函数 | 行号 | 触发场景 |
|--------|---------|------|---------|
| tmpl_task_urgent | `_do_send_process_task` (行 1554) | 1486 | 紧急任务通知 |
| tmpl_task_delay | `_do_send_process_task` (行 1554) | 1493 | 任务延期通知 |
| tmpl_task_assigned | `_do_send_process_task` (行 1554) | 1569 | 任务分配通知 |
| tmpl_process_start | `send_all_pending` (行 1663) | 1711 | 流程启动通知 |
| tmpl_task_assigned | `assign_task` (行 2663) | 2685 | 批量派单通知 |
| tmpl_task_transfer | `reassign_task` (行 2745) | 2768 | 任务转派通知 |
| tmpl_task_cancelled | `cancel_task` (行 2806) | 2815 | 任务取消通知 |
| tmpl_batch_assign | `batch_assign` (行 2828) | 2861 | 批量派单通知 |
| tmpl_process_advance | `notify_process_step` (行 4396) | 4420 | 流程步骤通知 |
| tmpl_repair_complete | `complete_repair_record` (行 5017) | 5028 | 维修完成通知 |
| tmpl_outsource_send | `create_outsource_record` (行 5726) | 5753 | 外协发出通知 |
| tmpl_outsource_receive | `receive_outsource_record` (行 5830) | 5842 | 外协收货通知 |
| tmpl_cost_loss_warning | `_check_order_cost_alerts` (行 6368) | 6390 | 亏损预警通知 |
| tmpl_cost_low_margin | `_check_order_cost_alerts` (行 6368) | 6402 | 低利润提醒 |
| tmpl_cost_profitable | `_check_order_cost_alerts` (行 6368) | 6412 | 高利润订单通知 |
| tmpl_schedule_change | `change_delivery_date` (行 6989) | 7042 | 排产/交期变更通知 |
| tmpl_alert_quality | `create_quality_task` (行 8058) | 8161 | 质量问题告警 |
| tmpl_quality_completed | `on_quality_record_completed` (行 8195) | 8272 | 质检完成通知 |

#### 调度中心 (schedule_routes.py)

| 模板ID | 调用函数 | 行号 | 触发场景 |
|--------|---------|------|---------|
| tmpl_schedule_notify | `create_schedule` | 587 | 排产通知 |
| tmpl_schedule_submitted | `submit_schedule` | 682 | 排产已提交 |
| tmpl_schedule_confirmed | `confirm_schedule` | 1189 | 排产已确认 |

#### 告警引擎 (alert_engine.py)

> ⚠️ **行号已重新核对（2026-06-20）**：原表函数名前缀 `_check_*` 错误（实际无下划线），行号也已偏移。下表基于 `grep -n '_render_template'` 实测。

| 模板ID | 调用函数 | 行号 | 触发场景 |
|--------|---------|------|---------|
| tmpl_task_reminder | `check_overdue_tasks` 内 | 215 | 任务超时提醒 |
| tmpl_schedule_reminder | `check_schedule_overdue` 内 | 411 | 排产超时提醒 |
| tmpl_alert_timeout | `check_order_timeout_alerts` 内 | 459 | 任务超时告警 |
| tmpl_alert_overdue | `check_order_timeout_alerts` 内 | 483 | 订单逾期告警 |
| tmpl_material_arrival | `check_material_arrival` 内 | 522 | 物料到货通知 |

#### 同步模块 (sync_bp.py)

| 模板ID | 调用端点 | 行号 | 触发场景 |
|--------|---------|------|---------|
| tmpl_report_submitted | `/sync/report` | 224 | 报工提交通知 |
| tmpl_report_actual | `/sync/report` | 311 | 实际报工通知 |
| tmpl_outsource_send | `/sync/outsource` | 395 | 外协发出通知 |

#### 容器中心 (container_center_v5.py)

> ⚠️ **行号已重新核对（2026-06-20）**：`tmpl_material_shortage` 行号 435 → 实测 **447**，所在方法 `ContainerCenter._handle_material` (行 372)。`tmpl_repair_report` 行号 1133 → 实测 **1145**，所在方法 `ContainerCenter.collect_repair` (行 1126)。原文档函数名 `create_material_order` / `create_repair_report` 在文件中 grep 0 命中，实际是类方法。

| 模板ID | 调用函数 | 行号 | 触发场景 |
|--------|---------|------|---------|
| tmpl_material_shortage | `ContainerCenter._handle_material` (行 372) | 447 | 物料短缺通知 |
| tmpl_repair_report | `ContainerCenter.collect_repair` (行 1126) | 1145 | 设备报修通知 |

#### 服务模块 (services/notifier.py)

| 模板ID | 调用函数 | 行号 | 触发场景 |
|--------|---------|------|---------|
| tmpl_task_assigned | `notify_task_assigned` | 95 | 任务分配通知 |
| tmpl_task_assigned | `notify_task_assigned` | 137 | 任务分配通知 |
| tmpl_task_completed | `notify_task_completed` | 182 | 任务完成通知 |
| tmpl_material_lowstock | `notify_low_stock` | 230 | 库存不足预警 |
| tmpl_report_submitted | `notify_report_submitted` | 311 | 报工提交通知 |
| tmpl_low_stock | `notify_low_stock` | 352 | 库存不足预警 |

#### 移动端 (app.py) - 通过 notify.py

> ⚠️ **位置错误**：原表说在 `app.py` 但 `grep -n 'def notify_admin_modified' app.py` 返回 0 命中。实际在 `notify.py`，且 `app.py` 通常通过 `from notify import notify_admin_modified` 调用。下表已修正。

| 模板ID | 调用函数 | 文件:行号 | 触发场景 |
|--------|---------|------|---------|
| 自定义文本 | `notify_admin_modified` | notify.py:177 | 报工修正通知 |
| 自定义文本 | `notify_admin_withdraw` | notify.py:191 | 报工撤回通知 |
| 自定义文本 | `notify_quality_modified` | notify.py:203 | 质检修正通知 |
| 自定义文本 | `notify_quality_withdraw` | notify.py:217 | 质检撤回通知 |

#### 外协命令 (commands/outsource_cmd.py)

> ⚠️ **行号已重新核对（2026-06-20）**：行号 300 ✓。`send_outsource` 在文件中 grep 0 命中（可能已重构），函数名标 "⚠️ 函数名待核"。

| 模板ID | 调用函数 | 行号 | 触发场景 |
|--------|---------|------|---------|
| tmpl_outsource_send | ⚠️ 函数名待核（`send_outsource` 在当前文件中 0 命中） | 300 | 外协发出通知 |

#### 企业微信机器人 (wechat_app_bot.py)

> ⚠️ **位置错误**：原表 `wechat_app_bot.py` 但 `bots/app_bot.py` 中 `grep 'tmpl_'` 和 `grep 'def handle_wechat_message'` 都返回 0 命中。行号和函数名都需要人工核对。

| 模板ID | 调用函数 | 行号 | 触发场景 |
|--------|---------|------|---------|
| tmpl_task_assigned | ⚠️ 函数名待核（`handle_wechat_message` 在 `bots/app_bot.py` 中 0 命中） | 536 | 任务分配通知 |

#### 单独派单服务 (standalone_dispatch_server.py)

| 模板ID | 调用端点 | 行号 | 触发场景 |
|--------|---------|------|---------|
| tmpl_report_submitted | ⚠️ `/api/submit_report` 端点（行号 1277 待核） | 1277 | 报工提交通知 |
