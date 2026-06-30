# FIFTH_AUDIT.md（数据库字段审计）

> 文档版本：v1.0（2026-06-13）
> 审计范围：6 个本地表 DDL × 业务代码 SQL 引用
> 审计方法：**假设每个字段引用都可能有 typo**

---

## 一、发现的 8 个 D 编号问题

### 🔴 D1: `process_records_local` 表 DDL 未创建

**问题**：`migrations/v1.1.0_module/002_local_mirror_tables.sql` 中**没有** `process_records_local` 表的 CREATE。

**被引用**：
- `etl_local_mirror.py:45` `_TARGET_TABLES`
- `etl_local_mirror.py:204` `sync_configs`
- `dispatch_center/schedule_routes.py:1162` `SELECT * FROM process_records_local`

**影响**：
- 5002 启动后 ETL 同步 process_records_local 会失败
- schedule_routes._query_mysql_workorders 永远抛 OperationalError(1146)

**修复**：补 DDL。

### 🔴 D2: process_sub_steps 字段不匹配（22 vs 9）

**源表 8008 写入字段**（22 个）：
```
uuid, process_id, process_record_id, order_no, step_name, batch_no,
quantity, qualified_qty, operator, operator_id, wechat_userid,
equipment_name, remark, record_date, source, overtime_hours,
synced, synced_at, created_at, updated_at, created_by, updated_by
```

**镜像表字段**（9 个）：
```
id, process_id, order_no, step_name, batch_no, quantity,
qualified_qty, operator, created_at
```

**缺失字段**（13 个）：
- process_record_id, operator_id, wechat_userid, equipment_name
- remark, record_date, source, overtime_hours
- synced, synced_at, updated_at, created_by, updated_by

**影响**：
- 业务层读 _local 表时 KeyError
- 报工追溯信息丢失（设备、备注、工时）

### 🔴 D3: 8008 主键字段 `uuid` vs 镜像表 `id`

**问题**：steel_belt.process_sub_steps 主键是 `uuid`，镜像表主键是 `id`。
- 8008 INSERT: `(uuid, process_id, ...)` - 主键叫 `uuid`
- 镜像表: `id VARCHAR(64) PRIMARY KEY`

**影响**：字段名不一致，未来维护混乱。

### 🔴 D4: `production_orders_local` 无 `id` 字段

**DDL**：
```sql
CREATE TABLE production_orders_local (
    order_no VARCHAR(50) PRIMARY KEY,  -- ← 主键是 order_no
    product_name, plan_start, plan_end, status, updated_at
    -- 没有 id 字段！
);
```

**代码引用**：
- `dispatch_center/_core.py:1095` `SELECT id, status, order_id FROM production_orders_local`
- `dispatch_center/_core.py:1120` `INSERT INTO production_orders_local (order_no, order_id, status, ...)`

**影响**：
- `SELECT id` 永远返回 `None`（不存在）
- `INSERT ... order_id` SQL 报错（字段不存在）

### 🔴 D5: `orders_local` 无 `id` 字段

**DDL**：
```sql
CREATE TABLE orders_local (
    order_no VARCHAR(50) PRIMARY KEY,  -- ← 主键是 order_no
    customer_group, customer_name, product_name, quantity, status,
    plan_start, plan_end, updated_at, created_at
);
```

**代码引用**：
- `dispatch_center/_core.py:1115` `SELECT id, order_no FROM orders_local`
- `dispatch_center/_core.py:1121` `o_row['id']` ← KeyError
- `dispatch_center/_core.py:1126` `SELECT id, status FROM orders_local`
- `dispatch_center/_core.py:1132` `UPDATE orders_local SET status=... WHERE id=%s` ← 字段不存在

**影响**：
- _sync_to_mysql 写路径会 KeyError 或 SQL 错误
- 排产状态变更业务挂掉

### 🔴 D6: `production_orders_local` 无 `order_id` 字段

**DDL**：无 `order_id` 字段

**代码引用**：
- `dispatch_center/_core.py:1120` `INSERT INTO production_orders_local (order_no, order_id, ...)` ← SQL 错误

### 🔴 D7: `violations_local` 字段名与源表不匹配

**源表 `violation_log` 字段**：
```
id, scenario, violation_type, severity, order_no, detail, created_at
```

**镜像表 DDL**：
```
id, scenario, severity, message, related_order, created_at
```

**不匹配字段**：
- 源表: `violation_type`, `order_no`, `detail`
- 镜像: `message`, `related_order`

**影响**：
- ETL 同步时 REPLACE INTO 失败
- 业务层读 _local 期望 `violation_type` 但表里叫 `message`

### 🟡 D8: ETL `SELECT *` 动态列适配性问题

**问题**：`etl_local_mirror.py:115-127` 用 `SELECT *` 然后动态构造 REPLACE INTO。

**风险**：
- 源表多了字段：REPLACE INTO 时多余字段值丢弃
- 源表少了字段：REPLACE INTO 缺字段，MySQL 用默认值
- 字段类型不匹配：bytes/None/特殊值处理已 OK

**结论**：当前基本能工作（被 try/except 兜底），但易脆。

---

## 二、字段匹配检查表

| 表 | 业务代码引用字段 | DDL 字段 | 匹配？ |
|----|------------------|----------|--------|
| orders_local | id, order_no, status, customer_group, customer_name, product_name, quantity, plan_start, plan_end, updated_at, created_at | order_no, customer_group, customer_name, product_name, quantity, status, plan_start, plan_end, updated_at, created_at | ❌ 缺 id |
| production_orders_local | id, status, order_id, order_no, plan_start, plan_end, updated_at, created_at | order_no, product_name, plan_start, plan_end, status, updated_at | ❌ 缺 id, order_id |
| violations_local | id, scenario, violation_type, severity, order_no, detail, message, related_order, created_at | id, scenario, severity, message, related_order, created_at | ❌ 字段名错 |
| process_records_local | (DDL 缺失) | (待建) | ❌ |
| work_orders_local | order_no, customer_name, product_name, quantity, status, is_deleted | order_no, customer_name, product_name, quantity, status, is_deleted, plan_start, plan_end, updated_at | ✅ |
| process_sub_steps_local | id, process_id, order_no, step_name, batch_no, quantity, qualified_qty, operator, created_at | 同上 | ✅（但少 13 个字段）|

---

## 三、累计修复统计

| 阶段 | 数量 |
|------|------|
| 之前累计 | 27 |
| **第五批 D 编号** | **8** |
| **总计** | **35** |

---

## 四、修复优先级

| 优先级 | 项 | 工作量 | 严重度 |
|--------|-----|--------|--------|
| **P0** | D1 process_records_local DDL 缺失 | 5min | 🔴 |
| **P0** | D4/D5/D6 id / order_id 字段缺失 | 30min | 🔴 |
| **P0** | D7 violation 字段名错 | 30min | 🔴 |
| **P1** | D2 process_sub_steps 字段补全 | 1h | 🟡 |
| **P1** | D3 字段名统一 uuid → id | 1h | 🟢 |
| **P2** | D8 ETL 显式列名 | 1h | 🟢 |

---

## 五、参考

- [ARCHITECTURE_AUDIT.md](./ARCHITECTURE_AUDIT.md) - 第 1 轮
- [POST_REFACTOR_AUDIT.md](./POST_REFACTOR_AUDIT.md) - 第 2 轮
- [FINAL_AUDIT.md](./FINAL_AUDIT.md) - 第 3 轮
- [FOURTH_AUDIT.md](./FOURTH_AUDIT.md) - 第 4 轮
- 本文档 - 第 5 轮（字段审计）

---

## 六、关键洞察

> **DDL 和 SQL 是最容易脱节的地方**。
> 我创建镜像表时只考虑"消除跨库直查"，**没有逐一对照**业务代码字段。
> 真实数据流会因字段缺失而**完全无法工作**。
> 字段审计必须是**静态分析 + 真实查询双重验证**。
