# chengsheng.db vs wechat_container.db 数据域逻辑关系定义

## 1. 角色定位

| 数据库 | 角色 | 所属系统 | 前端 |
|--------|------|---------|------|
| **chengsheng.db** | 晨圣报工主库 | legacy_routes.py | cs_report.html |
| **wechat_container.db** | 调度中心主库 | ContainerCenter + dispatch_center_bp | 调度中心页面 |

两者是**平级关系**，不是主从关系。各有归属的业务域。

## 2. 数据域全景

### 2.1 数据域总览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      晨圣报工业务域 (chengsheng.db)                        │
│                                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐           │
│  │ 订单      │  │ 工人     │  │ 报工记录  │  │ 考勤(已持久化) │           │
│  │ (orders) │  │ (workers)│  │(sub_steps)│  │ (attendance) │           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘           │
│                                                                         │
│  额外: process_records, order_processes, production_orders             │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                     调度中心业务域 (wechat_container.db)                  │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ 排产记录      │  │ 报工子步骤    │  │ 质检     │  │ 调度指令      │  │
│  │(process_     │  │(process_sub_ │  │(data_    │  │(dispatch_    │  │
│  │ records)     │  │ steps)       │  │ packages)│  │ commands)    │  │
│  └──────────────┘  └──────────────┘  └──────────┘  └──────────────┘  │
│                                                                         │
│  额外: order_cost, schedule_records, data_flow_logs, ...              │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 各数据域定义

| 编号 | 数据域 | 主库 | 从库 | 说明 |
|------|--------|------|------|------|
| **A** | **订单/排产** | chengsheng.db.orders | — | 订单数据只有chengsheng.db有一份，wechat_container.db无orders表；wechat_container.db的process_records通过order_no弱关联 |
| **B** | **工序定义** | chengsheng.db.order_processes | wechat_container.db.process_records.steps | chengsheng有独立的工序表，wechat_container是以JSON数组存在process_records.steps字段 |
| **C** | **报工子步骤** | **双库各自独立写入** | 互相同步 | 两个库都有子步骤数据：wechat_container.db通过ContainerCenter写入，chengsheng.db通过legacy_routes同步写入。目前是单向同步(→chengsheng.db) |
| **D** | **人员** | chengsheng.db.workers | container_config.json | 调度中心的操作员存在JSON配置文件，chengsheng.db的workers存在数据库。目前两个系统的人员完全独立管理 |
| **E** | **考勤** | **无**（当前在内存） | — | 考勤数据目前存在Python进程内存字典`_attendance_records`中，服务重启即丢失 |
| **F** | **质检** | wechat_container.db.data_packages | — | 质检数据存在调度中心的data_packages表(type='quality')，chengsheng.db无对应表 |
| **G** | **调度指令** | wechat_container.db | — | 调度指令、调度日志、数据流日志等为调度中心独有，与晨圣报工无直接关系 |
| **H** | **工单成本** | wechat_container.db.order_cost | — | 成本数据为调度中心独有 |

## 3. 当前数据流（现状）

### 3.1 晨圣报工前端操作时的数据流

```
cs_report.html 操作
│
├─ GET /api/dashboard        ──→  读 chengsheng.db.orders + sub_steps
├─ GET /api/scan-info        ──→  读 wechat_container.db(优先) → fallback 读 chengsheng.db
├─ POST /api/process_sub_step ──→  写 wechat_container.db + 写 chengsheng.db (双写)
├─ GET /api/sub_step_records  ──→  读 chengsheng.db.sub_steps
├─ GET /api/production-orders ──→  读 chengsheng.db.orders
├─ GET /api/workers           ──→  读 chengsheng.db.workers
├─ GET/POST /api/attendance   ──→  读/写 内存变量 (不落库)
└─ GET/POST /api/quality      ──→  读/写 wechat_container.db.data_packages
```

### 3.2 调度中心操作时的数据流

```
调度中心页面操作
│
├─ 排产创建  →  写 wechat_container.db.process_records  (完全绕过chengsheng.db)
├─ 报工管理  →  写 wechat_container.db.process_sub_steps
├─ 进度查看  →  读 wechat_container.db.process_records
├─ 操作员管理 →  读/写 container_config.json (JSON文件, 完全绕过chengsheng.db)
└─ 质检管理  →  读/写 wechat_container.db.data_packages
```

### 3.3 容器中心内部同步

```
ContainerCenter 内部
│
└─ add_sub_step()  ──→  写 wechat_container.db.process_sub_steps
                        └─ _sync_sub_step_to_chengsheng()  →  写 chengsheng.db.sub_steps
                            (当前唯一的自动同步点，单向)
```

## 4. 逻辑关系定义（目标）

### 4.1 数据域 A：订单/排产

```
定位：orders 归属 chengsheng.db（晨圣报工主库）
      process_records 归属 wechat_container.db（调度中心主库）
关联：通过 order_no 字段关联

关系：
  chengsheng.db.orders  ←── order_no ──→  wechat_container.db.process_records
  
  当调度中心新建排产时 → chengsheng.db.orders 应同步生成对应的订单记录
  当晨圣更新订单状态时 → process_records 应同步更新对应状态

数据所有权：
  chengsheng.db.orders         = 数据拥有者（增删改由此出发）
  wechat_container.db.process_records = 数据消费者（只读或被动同步）
  
关键约束：
  - process_records 的 order_no 必须能在 chengsheng.db.orders 中找到
  - 不能出现 wechat_container.db 有排产但 chengsheng.db 无对应订单的情况
```

### 4.2 数据域 B：工序

```
定位：工序定义归属于 chengsheng.db.order_processes
      wechat_container.db 以 JSON 存储在 process_records.steps

关系：
  chengsheng.db.order_processes  ──── 映射 ────  process_records.steps(JSON)

数据所有权：
  工序定义: chengsheng.db.order_processes = 数据拥有者
  工序状态: process_records.current_step + steps[].status = 调度中心控制

关键约束：
  - order_processes 的 sequence 顺序 = process_records.steps[] 的数组顺序
  - 工序名称在两个系统应该保持一致
```

### 4.3 数据域 C：报工子步骤

```
定位：双库各自独立写入，通过同步保持一致

关系：
  chengsheng.db.sub_steps  ◄──→  wechat_container.db.process_sub_steps
  
  - 晨圣报工前端报工 → 写入 wechat_container.db → 同步到 chengsheng.db
  - 调度中心报工     → 写入 wechat_container.db → 同步到 chengsheng.db
  
数据所有权：
  wechat_container.db.process_sub_steps = 数据拥有者（报工统一写入点）
  chengsheng.db.sub_steps = 数据副本（供晨圣报工查询）

关键约束：
  - sub_steps 的 process_id 必须能在 process_records 中找到
  - 两个数据库的子步骤数据必须最终一致
  - 同步延迟可接受（轮询秒级）
```

### 4.4 数据域 D：人员

```
定位：现在两套人员体系完全独立，需要统一

现有状态：
  chengsheng.db.workers          ← 晨圣报工工人数据（username + name + role）
  container_config.json          ← 调度中心操作员数据（id + name + role + department + enabled...）

目标关系：
  chengsheng.db.workers  ←── 数据主库 ──→  container_config（同步）

数据所有权：
  chengsheng.db.workers = 数据拥有者（人员新增/修改以chengsheng为准）
  container_config = 数据同步方（从chengsheng.db同步到调度中心）

关键约束：
  - 不允许在两个系统分别添加人员
  - 调度中心的操作员管理应改为读写chengsheng.db或同步
  - 人员信息（姓名、角色）必须一致
```

### 4.5 数据域 E：考勤

```
现状：内存变量，不持久化

目标：
  chengsheng.db.attendance  ←── 数据主库
  
  考勤数据统一持久化到 chengsheng.db.attendance 表

数据所有权：
  chengsheng.db.attendance = 数据拥有者

关键约束：
  - 服务重启后考勤数据不丢失
  - 考勤记录关联到 chengsheng.db.workers（通过 worker 名称关联）
```

### 4.6 数据域 F：质检

```
现状：质检数据存在 wechat_container.db.data_packages 中
      晨圣报工前端通过 legacy_routes 直接读写

数据所有权：
  wechat_container.db.data_packages(type='quality') = 数据拥有者

关系：
  质检数据可同步到 chengsheng.db（供晨圣报工离线查看）
  同步方向：wechat_container.db → chengsheng.db（单向即可）

关键约束：
  - 质检记录关联到 process_records（通过 related_order/order_no）
```

### 4.7 数据域 G + H：调度指令 + 成本

```
定位：调度中心独有，与晨圣报工无直接关系

数据所有权：
  wechat_container.db = 完全归属调度中心
  chengsheng.db 无对应数据

处理策略：
  不需要同步，保持独立。
```

## 5. 数据关系完整图

```
chengsheng.db                                 wechat_container.db
                                                
┌──────────────────────┐            ┌──────────────────────────────┐
│  orders              │            │  process_records             │
│  ┌───────────────┐   │   order_no │  ┌────────────────────────┐  │
│  │ order_id (PK) ├───┼────────────┼──┤ order_no               │  │
│  │ name          │   │            │  │ product_name            │  │
│  │ status        │   │            │  │ quantity / unit         │  │
│  │ material/spec │   │            │  │ status / current_step   │  │
│  │ delivery_date │   │            │  │ steps (JSON) ──→ 工序    │  │
│  │ priority      │   │            │  │ created_at / updated_at │  │
│  └───────────────┘   │            │  └────────────────────────┘  │
│                      │            │                              │
│  order_processes     │            │  process_sub_steps           │
│  ┌───────────────┐   │  同步(C域)  │  ┌────────────────────────┐  │
│  │ order_id      │   │            │  │ process_id              │  │
│  │ process_key   │   │            │  │ order_no / step_name    │  │
│  │ sequence      │   │            │  │ quantity / operator     │  │
│  └───────────────┘   │            │  │ batch_no / remark       │  │
│                      │            │  └────────────────────────┘  │
│  sub_steps           │            │                              │
│  ┌───────────────┐   │  ← 同步 ←  │  (子步骤同步)               │
│  │ step_id       │   │            │                              │
│  │ process_id    │   │            │  data_packages              │
│  │ order_no      │   │            │  ┌────────────────────────┐  │
│  │ step_name     │   │            │  │ type='quality' (质检F域) │  │
│  │ quantity      │   │            │  │ related_order            │  │
│  │ operator      │   │            │  │ content (质检内容)       │  │
│  └───────────────┘   │            │  │ type='inspection'(其他)  │  │
│                      │            │  └────────────────────────┘  │
│  workers             │            │                              │
│  ┌───────────────┐   │  同步(D域)  │  container_config.json     │
│  │ username (PK) ├───┼────────────┼──┤ 操作员列表               │
│  │ name          │   │            │  ┌────────────────────────┐  │
│  │ role          │   │            │  │ id / name              │  │
│  └───────────────┘   │            │  │ role / department      │  │
│                      │            │  │ enabled / max_tasks    │  │
│  attendance          │            │  └────────────────────────┘  │
│  ┌───────────────┐   │            │                              │
│  │ (待持久化)     │   │            │  ── 其他调度中心独有表 ──   │
│  └───────────────┘   │            │  order_cost, dispatch_     │
│                      │            │  commands, schedule_records │
│  quality_records     │            │  data_flow_logs, ...        │
│  ┌───────────────┐   │  ← 同步 ←  │                              │
│  │ (待新增)      │   │            │                              │
│  └───────────────┘   │            │                              │
└──────────────────────┘            └──────────────────────────────┘
```

## 6. 规则总结

### 6.1 数据归属规则

| 数据 | 谁的数据 | 谁可以改 | 谁只能读 |
|------|---------|---------|---------|
| 订单 (orders) | chengsheng.db | 晨圣报工/系统导入 | 调度中心可读 |
| 排产 (process_records) | wechat_container.db | 调度中心 | 晨圣报工可读 |
| 工序定义 | chengsheng.db | 晨圣报工 | 调度中心可读 |
| 工序状态 | wechat_container.db | 调度中心 | 晨圣报工可读 |
| 报工子步骤 | wechat_container.db(主) | 双方皆可写 | chengsheng.db同步一份 |
| 工人 | chengsheng.db | 晨圣报工 | 调度中心同步一份 |
| 考勤 | chengsheng.db | 晨圣报工 | 无 |
| 质检 | wechat_container.db | 调度中心 | chengsheng.db同步一份 |
| 调度指令/成本 | wechat_container.db | 调度中心 | 晨圣报工不需要 |

### 6.2 同步方向汇总

| 域 | 同步方向 | 同步必要性 |
|----|---------|-----------|
| A 订单 | process_records → orders (新排产产生新订单) | ✅ 必须 |
| A 订单状态 | orders → process_records (状态同步) | ✅ 必须 |
| C 子步骤 | wechat_container.db ↔ chengsheng.db (双向一致) | ✅ 已有，可优化 |
| D 人员 | chengsheng.db → container_config (工人同步到操作员) | ✅ 必须 |
| E 考勤 | 内存 → chengsheng.db (持久化) | ✅ 必须 |
| F 质检 | wechat_container.db → chengsheng.db (质检记录同步) | ⭕ 可选 |

### 6.3 强制约束

1. **不允许数据孤岛**: 调度中心新建排产，chengsheng.db必须有对应订单
2. **人员统一**: 不允许两套人员体系长期不一致
3. **考勤持久化**: 不允许考勤数据只在内存中
4. **引用完整性**: process_sub_steps.process_id 必须能在 process_records 中找到
5. **最终一致性**: 所有同步数据允许秒级延迟，但不允许永久不一致
