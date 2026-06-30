# 数据库审计报告 v3 - ARCHITECTURE_v3.6.md（第三轮 - 数据库工程师视角）

> **审计范围**：`mobile_api_ai/docs/ARCHITECTURE_v3.6.md`（v3.6.8）
> **审计文件**：`mobile_api_ai/cloud_relay.py`（873 行，9 张表查询函数在 200-500 行）
> **审计视角**：数据库工程师（DBA / SQL 性能 / 数据一致性）
> **审计日期**：2026-06-24
> **前置审计**：第一轮（25 项，6 项修复）+ 第二轮（19+8 项未完成）

---

## 一、前两轮审计修复状态确认

### ✅ 第一轮 6 项 D-类问题修复情况

| # | 第一轮问题 | 修复状态 | 证据 |
|---|-----------|:--------:|------|
| D-1 | CASE WHEN 14点边界重叠 | ✅ 已修复 | cloud_relay.py:215-216 改为 `WHEN 6,7,8,9,10,11,12,13 THEN '早班'`、`WHEN 14,15,16,17,18,19,20,21,22 THEN '中班'` |
| D-2 | JSON 函数无容错 | ⚠️ 部分修复 | `_q_workorder_progress` 仍无 try/except 保护 JSON_EXTRACT |
| D-3 | inventory_weekly 无 LIMIT | ✅ 已修复 | cloud_relay.py:443-448 增加了 `w.is_active=1`、`deleted_at IS NULL`、3 个 `w.name NOT LIKE` 过滤 |
| D-4 | substep_recent 默认 limit=100 | ✅ 已修复 | cloud_relay.py:374 `limit: int = 500`，调用方 line 612 `limit=500` |
| D-5 | R-001 适用范围模糊 | ✅ 已修复 | ARCHITECTURE_v3.6.md:222 明确"统计表批量只读查询（container_center / inventory 数据库）允许直接连接，属于特例；涉及写入的操作禁止直连" |
| D-6 | 连接池无文档说明 | ⚠️ 部分修复 | ARCHITECTURE 第 6.7.5 节环境变量表已列出 INVENTORY/CONTAINER 环境变量，但**未说明 PooledDB 配置**（maxconnections=10/mincached=2/maxcached=5） |

### ✅ 第二轮 8 项新增问题修复情况

| # | 第二轮问题 | 修复状态 | 证据 |
|---|-----------|:--------:|------|
| N-1 | ASCII 架构图标题 v3.6.5 | ✅ 已修复 | ARCHITECTURE_v3.6.md:140 显示"v3.6.8 架构（N-1 改造后）" |
| N-4 | 5003 /api/stats/push 冲突 | ✅ 已修复 | standalone_dispatch_server.py:105, 274 注释明确"已迁移到 5005"，端点代码已删除 |
| N-7 | 同 N-4 | ✅ 已修复 | 5003 端点代码已删除（line 275-338 旧代码已删除） |

---

## 二、仍存在的 SQL 性能 / 正确性问题（按严重度排序）

### 🔴 P0-A：MySQL 简单 CASE WHEN 语法错误（语法不合法）

**位置**：`mobile_api_ai/cloud_relay.py:214-218`

```sql
CASE HOUR(pr.created_at)
    WHEN 6,7,8,9,10,11,12,13 THEN '早班'
    WHEN 14,15,16,17,18,19,20,21,22 THEN '中班'
    ELSE '晚班'
END AS 班组
```

**问题描述**：
MySQL 简单 CASE 表达式语法为 `CASE expr WHEN val1 THEN ... WHEN val2 THEN ...`，**每个 WHEN 只能接受单个值**，逗号分隔的多值列表**不是合法 MySQL 语法**。

**影响**：
- 实际执行时 MySQL 会抛出 `ERROR 1064 (42000): You have an error in your SQL syntax`
- `_q_production_daily` 在生产日报 cron 触发时**每次都会失败**
- 9 张统计表中的 `production_daily_report` 表实际上**永远推送不到云端 5004**

**修复建议**：
```sql
CASE
    WHEN HOUR(pr.created_at) BETWEEN 6 AND 13 THEN '早班'
    WHEN HOUR(pr.created_at) BETWEEN 14 AND 22 THEN '中班'
    ELSE '晚班'
END AS 班组
```

或使用 IN 列表形式：
```sql
CASE
    WHEN HOUR(pr.created_at) IN (6,7,8,9,10,11,12,13) THEN '早班'
    WHEN HOUR(pr.created_at) IN (14,15,16,17,18,19,20,21,22) THEN '中班'
    ELSE '晚班'
END AS 班组
```

**严重度**：🔴 P0 - 阻塞核心功能，9 张表定时任务中 1 张事实上无法工作。

---

### 🔴 P0-B：inventory_monthly 期初数量硬编码为 0（数据错误）

**位置**：`mobile_api_ai/cloud_relay.py:466-497`（特别是 line 489-490）

```python
for r in rows:
    inbound = r.get('入库数量') or 0
    outbound = r.get('出库数量') or 0
    r['期初数量'] = 0  # ❌ 硬编码为 0
    r['期末数量'] = r['期初数量'] + inbound - outbound  # ❌ 等于入库-出库
    r['期末金额'] = round(r['期末数量'] * (r.get('单价') or 0), 2)
```

**问题描述**：
物料收发存汇总表的核心是计算"期末库存"，但代码将期初数量硬编码为 0，导致：
- `期末数量 = 0 + 入库数量 - 出库数量 = 净变动量`
- 这与"上月末库存 + 本月入库 - 本月出库 = 本月末库存"的会计准则**完全相反**

**业务影响**：
- 物料收发存汇总（`inventory_monthly_summary`）的"期末数量"和"期末金额"是**错误数据**
- 财务核算、成本计算、呆滞库存分析**全部基于错误数据**
- 月初首次运行时无对比基准，月内任意时刻查询也是错值

**修复建议**：
```python
# 期初数量 = SUM(本月之前的库存变动) + 上月期末结转
# 实际方案：调用 inventory.inventory 表的 current_qty 减去本月变动
# 简化方案：子查询
# 期末数量 = SUM(CASE WHEN it.created_at <= LAST_DAY(...) THEN ... END)
```

**严重度**：🔴 P0 - 核心业务数据错误，影响财务核算与决策。

---

### 🟠 P1-A：_q_inventory_weekly 存在 N+1 查询问题

**位置**：`mobile_api_ai/cloud_relay.py:431-463`

```python
def _q_inventory_weekly(week_start: date, week_end: date) -> List[Dict[str, Any]]:
    # 主查询返回 N 行（每个仓库一行）
    for r in rows:
        r['库存余额'] = _q_inventory_balance(conn, r['仓库'])      # ❌ N 次查询
        r['库存金额'] = _q_inventory_value(conn, r['仓库'])        # ❌ N 次查询
```

**问题描述**：
- 主查询返回 N 个仓库的周报表数据
- 对每个仓库，循环调用 `_q_inventory_balance` 和 `_q_inventory_value`
- 总查询次数 = `1 + 2N`
- 如果有 10 个仓库，每周产生 21 次查询
- 9 张表中**唯一**使用这种模式的地方

**性能影响**：
- 9 张表每周一 09:00 触发一次，但同时可能多个表并发
- 9 × 21 = 189 次/触发 × 52 周 = 9828 次/年额外查询
- 数据库连接池 `maxconnections=10` 可能被这些短查询耗尽
- 网络往返延迟累计 189 × 平均 1ms = 189ms 额外延迟

**修复建议**：
将 `_q_inventory_balance` 和 `_q_inventory_value` 合并到主查询中：
```sql
SELECT
    w.name AS 仓库,
    SUM(CASE WHEN it.type='in' THEN it.qty ELSE 0 END) AS 入库数,
    SUM(CASE WHEN it.type='out' THEN it.qty ELSE 0 END) AS 出库数,
    COUNT(*) AS 异动笔数,
    -- 单次 JOIN 解决余额和金额
    (SELECT COALESCE(SUM(inv.current_qty), 0) 
     FROM inventory.inventory inv 
     WHERE inv.warehouse_id = w.id) AS 库存余额,
    (SELECT COALESCE(SUM(inv.current_qty * p.last_purchase_price), 0)
     FROM inventory.inventory inv
     INNER JOIN inventory.products p ON p.id = inv.product_id
     WHERE inv.warehouse_id = w.id AND p.deleted_at IS NULL) AS 库存金额
FROM inventory.inventory_transactions it
LEFT JOIN inventory.warehouses w ON w.id = it.warehouse_id
WHERE DATE(it.created_at) BETWEEN %s AND %s
  AND w.is_active = 1 AND w.deleted_at IS NULL
  AND w.name NOT LIKE '测试%' AND w.name NOT LIKE 'temp%' AND w.name NOT LIKE '样仓%'
GROUP BY w.id, w.name
```

**严重度**：🟠 P1 - 性能可优化点，每周仅 1 次触发，但 N+1 是反模式。

---

### 🟠 P1-B：_q_inventory_alert LEFT JOIN 无日期范围限制

**位置**：`mobile_api_ai/cloud_relay.py:500-538`

```sql
FROM inventory.inventory inv
INNER JOIN inventory.inventory_products p ON p.id = inv.product_id
INNER JOIN inventory.warehouses w ON w.id = inv.warehouse_id
LEFT JOIN inventory.inventory_transactions it
    ON it.product_id = inv.product_id AND it.warehouse_id = inv.warehouse_id
WHERE p.deleted_at IS NULL
  AND w.is_active = 1
  AND w.deleted_at IS NULL
GROUP BY p.id, w.id, inv.current_qty
HAVING 当前库存 < %s
```

**问题描述**：
- `LEFT JOIN inventory_transactions` 仅按 product_id+warehouse_id 关联，**没有日期范围过滤**
- 对每条 inventory 行，MySQL 会关联**所有历史 transactions**（可能数百万行）
- 实际只需要 `MAX(it.created_at)`，但全表扫描 + GROUP BY 后才过滤
- 库存表即使只有几千个 SKU，inventory_transactions 可能数千万行

**性能影响**：
- 该查询每天 09:00 触发，伴随库存表的全表扫描
- 即便有 `idx_trans_product_type` 索引（migration:273），也无法避免 GROUP BY 前的全量数据加载
- 慢查询日志中很可能出现这条

**修复建议**：
```sql
LEFT JOIN inventory.inventory_transactions it
    ON it.product_id = inv.product_id 
    AND it.warehouse_id = inv.warehouse_id
    AND it.created_at >= DATE_SUB(NOW(), INTERVAL 365 DAY)  -- 限定时间窗口
```

**严重度**：🟠 P1 - 慢查询风险，数据量增长后会显著恶化。

---

### 🟠 P1-C：_q_inventory_slow_moving 同样问题 + MAX(it.created_at) 当 NULL 时

**位置**：`mobile_api_ai/cloud_relay.py:541-581`

```python
def _q_inventory_slow_moving(days_threshold: int = 90) -> List[Dict[str, Any]]:
    sql = """
        SELECT
            ...
            MAX(it.created_at) AS 最后异动日期,
            DATEDIFF(NOW(), MAX(it.created_at)) AS 库龄,
            ...
        FROM inventory.inventory inv
        ...
        LEFT JOIN inventory.inventory_transactions it
            ON it.product_id = inv.product_id
        ...
        HAVING 库龄 > %s
    """
```

**问题描述**：
- 同样的 LEFT JOIN 全量问题
- **额外问题**：`MAX(it.created_at)` 为 NULL 时（从未异动的库存），`DATEDIFF(NOW(), NULL)` 返回 NULL，无法通过 `HAVING 库龄 > %s` 过滤
- 这些"从未异动"的呆滞料会被漏掉
- 业务上"从未入库/出库的库存"恰恰是**最严重的呆滞料**

**修复建议**：
```sql
COALESCE(MAX(it.created_at), inv.created_at) AS 最后异动日期,
DATEDIFF(NOW(), COALESCE(MAX(it.created_at), inv.created_at)) AS 库龄,
HAVING 库龄 IS NOT NULL AND 库龄 > %s
```

**严重度**：🟠 P1 - 业务规则错误 + 性能问题。

---

### 🟠 P1-D：_q_workorder_progress 无 LIMIT、无 ORDER BY

**位置**：`mobile_api_ai/cloud_relay.py:313-355`

```sql
SELECT ...
FROM container_center.process_records pr
WHERE pr.order_no IS NOT NULL
  AND pr.order_no != ''
  AND pr.status NOT IN ('completed', 'cancelled')
```

**问题描述**：
- 没有任何 `LIMIT` / `ORDER BY`
- 系统中可能有成千上万个"进行中"工单
- 每 4 小时定时触发一次，触发时全量返回
- 配合 `JSON_LENGTH` / `JSON_EXTRACT`，每行都做 JSON 解析，开销很大

**潜在风险**：
- 网络传输：1 万行 × 13 列 = 数十万字段
- 内存：每个 Dict 对象 × 10000 = 可能 OOM
- 云端 5004 接收后处理压力

**修复建议**：
```sql
ORDER BY pr.updated_at DESC
LIMIT 1000  -- 最近 1000 条未完成工单
```

**严重度**：🟠 P1 - 数据量小时无问题，增长后是高风险点。

---

### 🟠 P1-E：_q_workorder_progress JSON 函数无容错

**位置**：`mobile_api_ai/cloud_relay.py:322-334`

```sql
CASE WHEN pr.current_step >= JSON_LENGTH(pr.steps)
     THEN pr.updated_at ELSE NULL END AS 实际完工,
CASE
    WHEN pr.steps IS NOT NULL
         AND pr.current_step < JSON_LENGTH(pr.steps)
    THEN JSON_UNQUOTE(JSON_EXTRACT(
        pr.steps,
        CONCAT('$[', pr.current_step, '].name')
    ))
    ELSE NULL
END AS 当前工序,
```

**问题描述**：
- 当 `pr.steps` 是 NULL 时，`JSON_LENGTH(NULL)` 返回 NULL，比较 `current_step < NULL` 也返回 NULL
- `JSON_EXTRACT` 在 NULL 输入时返回 NULL，**整体查询不会报错**
- 但当 `pr.steps` 是**非 NULL 但不是合法 JSON 字符串**时（数据损坏）：
  - `JSON_LENGTH('not json')` 会返回 NULL，行为 OK
  - `JSON_EXTRACT('not json', '$[0].name')` 会抛 ERROR
- 整条 SQL 失败，整个工单进度表无法推送

**修复建议**：
- 在 Python 层 try/except 单行处理：
```python
for r in rows:
    try:
        total = json.loads(r.get('总工序') or 0)  # 已有 current_step，不需 JSON
        ...
    except Exception as e:
        logger.warning(f'工单进度 JSON 解析失败 {r["工单号"]}: {e}')
        r['当前工序'] = None
```

或在 SQL 层使用 JSON_VALID：
```sql
CASE WHEN JSON_VALID(pr.steps) = 1 AND pr.current_step < JSON_LENGTH(pr.steps)
     THEN JSON_UNQUOTE(...)
     ELSE NULL END
```

**严重度**：🟠 P1 - 防御性编程，单行数据污染整表。

---

### 🟡 P2-A：_q_production_daily WHERE 字段与 CASE 字段不一致

**位置**：`mobile_api_ai/cloud_relay.py:213-225`

```sql
SELECT
    DATE(pr.plan_start) AS 日期,         -- ← 使用 plan_start
    CASE HOUR(pr.created_at)            -- ← 使用 created_at
        WHEN 6,7,8,... THEN '早班'
        ...
    END AS 班组,
    ...
WHERE pr.plan_start IS NOT NULL
  AND DATE(pr.plan_start) = %s          -- ← 过滤 plan_start
```

**问题描述**：
- 报告按 `plan_start` 日期分组（"今天的计划"）
- 但"早班/中班/晚班"基于 `created_at` 小时
- 典型场景：21:00 创建工序，00:30 实际开始，第二天 06:00 报工
  - `plan_start` = 当天
  - `created_at` 小时 = 6（早班）
  - 实际报工班次是早班，但工序记录在 `plan_start` 当天的"晚班"统计里
- 数据语义混乱

**修复建议**：
- 改用 `DATE(pr.record_date)` 或统一使用 `plan_start` 的小时
- 业务确认后二选一

**严重度**：🟡 P2 - 业务理解问题，不影响功能但数据可信度打折。

---

### 🟡 P2-B：_q_inventory_weekly YEARWEEK 参数化但常量化

**位置**：`mobile_api_ai/cloud_relay.py:440, 454`

```sql
YEARWEEK(%s, 3) AS 周次
...
c.execute(sql, (week_start, week_start, week_end))  # 3 个参数
```

**问题描述**：
- `YEARWEEK(%s, 3)` 接收参数 `week_start`，但实际值已知
- 用参数化反而让 MySQL 每次执行时类型转换（DATE → INT）
- 应该直接拼接字面量或使用 `YEARWEEK(DATE(%s), 3)` 让 MySQL 自动转换

**严重度**：🟡 P2 - 微小性能损失，但语义不清晰。

---

### 🟡 P2-C：_q_inventory_weekly LEFT JOIN 实为 INNER JOIN

**位置**：`mobile_api_ai/cloud_relay.py:441-449`

```sql
FROM inventory.inventory_transactions it
LEFT JOIN inventory.warehouses w ON w.id = it.warehouse_id
WHERE DATE(it.created_at) BETWEEN %s AND %s
  AND w.is_active = 1
  AND w.deleted_at IS NULL
  AND w.name NOT LIKE '测试%'
  AND w.name NOT LIKE 'temp%'
  AND w.name NOT LIKE '样仓%'
GROUP BY w.id, w.name
```

**问题描述**：
- 使用 LEFT JOIN，但 WHERE 子句强制 `w.is_active=1`、`w.deleted_at IS NULL`
- 这等价于 INNER JOIN
- 误导代码阅读者

**修复建议**：
```sql
FROM inventory.inventory_transactions it
INNER JOIN inventory.warehouses w ON w.id = it.warehouse_id
WHERE ...
```

**严重度**：🟡 P2 - 可读性问题，性能等价。

---

### 🟡 P2-D：HAVING 子句引用列别名（可移植性）

**位置**：`mobile_api_ai/cloud_relay.py:518, 560`

```sql
HAVING 当前库存 < %s  -- line 518
HAVING 库龄 > %s      -- line 560
```

**问题描述**：
- `HAVING` 引用 SELECT 别名（`当前库存`/`库龄`）是 MySQL 扩展
- PostgreSQL / SQL Server 不支持
- 当前项目锁定 MySQL，无实际影响，但降低可移植性

**严重度**：🟡 P2 - 锁定 MySQL 可接受。

---

## 三、连接池配置分析

### 当前配置对比

| 位置 | maxconnections | mincached | maxcached | ping | 备注 |
|------|:----:|:----:|:----:|:----:|------|
| `cloud_relay.py:96-98` (5005) | **10** | **2** | **5** | 1 | 9 张表 + API |
| `core/db_compat.py:38` (主应用) | 50 | 5 | 15 | 1 | 5008/5003/5010 共用 |

### 配置评估

**问题 1：5005 池偏小**
- APScheduler 同时可能运行**多个**表任务（虽然有 `threading.Lock`，但跨表并发仍可能）
- `_q_inventory_weekly` 在循环中调用 `_q_inventory_balance` + `_q_inventory_value`
  - 10 个仓库 = 21 次查询，可能在 1-2 秒内连续获取连接
  - 同时 `/api/stats/trigger/<table_type>` 端点可能接收外部请求
  - 触发 `pool full` 警告后阻塞（`blocking=True`），导致响应延迟

**问题 2：池大小差异原因未文档化**
- 为什么 5005 用 10，主应用用 50？
- 文档中无说明

**修复建议**：
1. 5005 池提升至 `maxconnections=20, mincached=5, maxcached=10`
2. 在 ARCHITECTURE 文档 6.7.5 节补充：
```markdown
| 参数 | cloud_relay.py (5005) | core/db_compat.py (主应用) | 说明 |
|------|:----:|:----:|------|
| maxconnections | 20 | 50 | 5005 仅 9 张表推送，负载轻 |
| mincached | 5 | 5 | 预热连接数 |
| maxcached | 10 | 15 | 缓存池上限 |
| blocking | True | True | 池满时阻塞等待 |
| ping | 1 | 1 | 使用前 ping 检查 |
```

**严重度**：🟡 P2 - 当前规模够用，但留扩容文档和配置参考。

---

## 四、索引覆盖分析

### 4.1 现状调研

| 表 | 关键查询条件 | 现有索引 | 评估 |
|-----|------------|---------|------|
| `container_center.process_records` | `plan_start, process_type` | `process_records_local` 中 `idx_status`, `idx_step`（**无 plan_start 索引**） | ❌ 缺 |
| `container_center.process_sub_steps` | `created_at, is_deleted, record_date, equipment_name` | `process_sub_steps_local` 中 `idx_order, idx_step, idx_batch` | ❌ 缺 created_at 索引 |
| `container_center.process_records` | `status NOT IN (...), order_no` | — | ❌ 缺 (status) 索引 |
| `inventory.inventory` | `warehouse_id, product_id` | `idx_inv_wh_product`（migration:255） | ✅ 已建 |
| `inventory.inventory_transactions` | `created_at, product_id, type, warehouse_id` | `idx_trans_created` (line 267), `idx_trans_product_type` (line 273) | ✅ 已建 |
| `inventory.products` | `deleted_at` | `idx_products_deleted` (line 226) | ✅ 已建 |
| `inventory.warehouses` | `deleted_at, is_active` | `idx_warehouses_deleted` (line 243) | ✅ 已建 |

### 4.2 关键缺失索引（建议补充）

#### 4.2.1 `process_records.plan_start` 索引
**理由**：`_q_production_daily` 和 `_q_production_monthly` 都按 `plan_start` 过滤，**当前无索引会导致全表扫描**。

```sql
CREATE INDEX idx_process_records_plan_start
ON container_center.process_records(plan_start);
```

#### 4.2.2 `process_records(process_type, status)` 复合索引
**理由**：生产日报过滤 `process_type='production' AND status NOT IN (...)`，可走复合索引。

```sql
CREATE INDEX idx_process_records_type_status
ON container_center.process_records(process_type, status);
```

#### 4.2.3 `process_sub_steps(created_at, is_deleted)` 复合索引
**理由**：`_q_substep_recent` 按 `created_at DESC` 排序 + `is_deleted=0` 过滤；`_q_workshop_capacity` 同样按日期过滤。

```sql
CREATE INDEX idx_pss_created_deleted
ON container_center.process_sub_steps(created_at DESC, is_deleted);
```

#### 4.2.4 `process_sub_steps(equipment_name, record_date)` 复合索引
**理由**：`_q_workshop_capacity` 按 `equipment_name` 分组，按 `record_date` 过滤。

```sql
CREATE INDEX idx_pss_equipment_record_date
ON container_center.process_sub_steps(equipment_name, record_date);
```

**严重度**：🟠 P1 - 缺索引是性能硬伤，迁移脚本未同步 9 张表的需求。

---

## 五、跨库查询与 R-001 合规性分析

### 5.1 5005 直连情况清单

| 表 | 所属库 | 库所有者 | 5005 直连？ | 是否 R-001 违反 |
|-----|--------|---------|:-----------:|:-----------:|
| `container_center.process_records` | container_center | 5002 | ✅ 是 | 视文档 |
| `container_center.process_sub_steps` | container_center | 5002 | ✅ 是 | 视文档 |
| `inventory.inventory` | inventory | 5010 | ✅ 是 | 视文档 |
| `inventory.inventory_transactions` | inventory | 5010 | ✅ 是 | 视文档 |
| `inventory.products` | inventory | 5010 | ✅ 是 | 视文档 |
| `inventory.warehouses` | inventory | 5010 | ✅ 是 | 视文档 |

### 5.2 R-001 合规性判定

**R-001 原文**："禁止在服务 A 中直接连接服务 B 的数据库，必须通过 API 接口交互"

**ARCHITECTURE_v3.6.md:222 补充**：
> "统计表批量只读查询（container_center / inventory 数据库）允许直接连接，属于特例；涉及写入的操作禁止直连。"

**判定结果**：
- ✅ **R-001 特例成立**：9 张表查询都是**批量只读**，无 INSERT/UPDATE/DELETE
- ✅ **架构合理**：5005 直接 POST 云端 5004，链路 2 跳（5005→5004），比 3 跳（5005→5003→5004）少一次 HTTP 往返
- ⚠️ **风险点**：
  1. **数据一致性靠应用层维护**：5005 直连意味着如果 5002/5010 改表结构，5005 不会感知
  2. **权限边界模糊**：5005 需要 container_center 和 inventory 两个库的只读权限
  3. **失败回滚路径未文档化**：如果 5002/5010 临时不可达，5005 应如何降级

### 5.3 风险缓解建议

1. **添加数据库 schema 版本检查**：
   ```python
   # 启动时检查关键表结构
   def _check_schema_version():
       conn = _get_conn('container_center')
       try:
           with conn.cursor() as c:
               c.execute("""
                   SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
                   WHERE TABLE_SCHEMA='container_center'
                   AND TABLE_NAME='process_records'
                   AND COLUMN_NAME IN ('plan_start', 'current_step', 'steps')
               """)
               if len(c.fetchall()) < 3:
                   raise RuntimeError("container_center.process_records schema mismatch")
       finally:
           conn.close()
   ```

2. **补充 R-001 例外的边界条件**到 ARCHITECTURE：
```markdown
### R-001 例外条件（5005 统计表推送）
1. 仅限批量只读查询（SELECT ... GROUP BY ...）
2. 9 张表白名单：见 cron 时间表
3. 写操作仍禁止直连（如发生，需走对应服务 API）
4. 表结构变更需同步通知 5005 维护者
```

**严重度**：🟡 P2 - 文档合规性可补强，技术上无违规。

---

## 六、事务一致性与并发分析

### 6.1 9 张表导出函数的事务边界

```python
def _q_production_daily(target_date: date) -> List[Dict[str, Any]]:
    conn = _get_conn('container_center')
    try:
        with conn.cursor() as c:
            c.execute(sql, (target_date,))
            rows = c.fetchall()
        # ⚠️ fetchall 之后，rows 是 Python 列表
        # 后续的 r['差异率'] = ... 等修改不影响数据库
    finally:
        conn.close()  # 连接立即关闭
```

**评估**：
- ✅ 所有查询都是**只读**，无数据修改，无事务一致性需求
- ✅ 连接立即关闭（`conn.close()`），不持有数据库锁
- ✅ `_autocommit=True` 设置正确（cloud_relay.py:74）
- ⚠️ 但 `conn.close()` 实际是**归还连接到池**，不是真正关闭，命名易误导

### 6.2 并发控制

**当前设计**：
- 每个表用 `threading.Lock` 保护（cloud_relay.py:197）
- `max_instances=1`（cloud_relay.py:784）确保同一任务不并发

**评估**：
- ✅ 同一表不会并发执行
- ⚠️ **不同表可能并发**：9 个 APScheduler 任务在重叠时段触发
- ⚠️ **手动触发可能与定时任务并发**：`/api/stats/trigger/<table_type>` 端点也会调用 `_export_table`
- ⚠️ **锁粒度合理**：按表锁定，避免全局锁

**修复建议**：
1. 给 `_stats_locks` 加超时机制，避免长任务阻塞后续执行：
```python
if not _stats_locks[table_type].acquire(timeout=300):
    logger.warning(f'{table_type} 任务超时未完成，跳过本次')
    return {'code': -1, 'message': '任务正在执行中'}
```

**严重度**：🟡 P2 - 防御性改进，非紧急。

---

## 七、新发现的问题（按严重度排序）

### 🟠 P1-F：inventory.inventory_transactions 范围查询无下界保护

**位置**：`mobile_api_ai/cloud_relay.py:443`

```sql
WHERE DATE(it.created_at) BETWEEN %s AND %s
```

**问题描述**：
- 周报场景：查询本周一至周日数据
- 但如果数据量极大（千万级），BETWEEN 扫描成本高
- 缺少 `created_at >= DATE_SUB(NOW(), INTERVAL 90 DAY)` 这种下界保护

**修复建议**：
- 周报场景默认 7 天，索引已建（`idx_trans_created`），性能可接受
- 但建议**增加 HINT 强制索引**：
```sql
FROM inventory.inventory_transactions it USE INDEX (idx_trans_created)
```

**严重度**：🟡 P2 - 数据量大时才需优化。

---

### 🟠 P1-G：_q_inventory_balance/value 在异常时无错误处理

**位置**：`mobile_api_ai/cloud_relay.py:406-428`

```python
def _q_inventory_balance(conn, warehouse_name: str) -> float:
    with conn.cursor() as c:
        c.execute("""...""", (warehouse_name,))
        row = c.fetchone()
    return float(row['total']) if row else 0.0
```

**问题描述**：
- 异常（如 `row` 为 None 但访问 `row['total']`）会冒泡到 `_q_inventory_weekly` 的 `for r in rows` 循环
- 单个仓库查询失败会导致**整个周报失败**
- 应该单独 try/except 让其他仓库的查询继续

**修复建议**：
```python
def _q_inventory_balance(conn, warehouse_name: str) -> float:
    try:
        with conn.cursor() as c:
            c.execute("""...""", (warehouse_name,))
            row = c.fetchone()
        return float(row['total']) if row else 0.0
    except Exception as e:
        logger.warning(f'仓库 {warehouse_name} 库存余额查询失败: {e}')
        return 0.0
```

**严重度**：🟠 P1 - 一个仓库异常阻断全部。

---

### 🟠 P1-H：_calc_pct 公式 bug：合格率计算错误

**位置**：`mobile_api_ai/cloud_relay.py:235`

```python
r['差异率'] = _calc_pct((r.get('完成数') or 0) - (r.get('计划数') or 0), r.get('计划数'))
r['合格率'] = _calc_pct(r.get('完成数'), r.get('完成数'), 100)  # ❌ 错误
```

**问题描述**：
- `r['合格率'] = _calc_pct(完成数, 完成数, 100)` 中分子分母都是 `完成数`
- 应该是 `_calc_pct(合格数, 完成数, 100)`（合格数/完成数）
- 当前结果永远返回 100%
- 同时 `_q_workshop_capacity` 也有相同问题（line 305）

**严重建议**：
- 需要在字段映射中增加"合格数"字段
- 或者用 `r.get('完成数')` 当作分子（仅当不区分合格/完成时合理，但生产日报需要区分）

**严重度**：🟠 P1 - 数据正确性问题，9 张表中**两个表**的合格率是假数据。

---

### 🟡 P2-E：_calc_pct 公式里 `(qty or 0) - (qty or 0)` 永远为 0

**位置**：`mobile_api_ai/cloud_relay.py:235`

```python
r['差异率'] = _calc_pct((r.get('完成数') or 0) - (r.get('计划数') or 0), r.get('计划数'))
```

**问题描述**：
- `(完成数 - 计划数) / 计划数 * 100` 应该是"差异率"
- 但 `_calc_pct` 函数（line 103-106）的语义是"百分比"
- 差异率可以是负数（未完成），但 `_calc_pct` 没有处理负数逻辑

**严重度**：🟡 P2 - 业务理解问题，不影响功能。

---

### 🟡 P2-F：云端 5004 推送 payload 包含敏感信息

**位置**：`mobile_api_ai/cloud_relay.py:667-690`

```python
payload = {
    'table_type': table_type,
    'period_key': period_key or '',
    'batch_id': batch_id,
    'record_hash': record_hash,
    'records': _map_to_field_ids(table_type, records),  # 全部数据
}
```

**问题描述**：
- `records` 中包含客户名、产品名、单价等敏感信息
- 当前用 `X-API-Key` 鉴权，但**未使用 HTTPS**（line 687 `http://`）
- 如果 CLOUD_5004 是公网 IP，敏感数据明文传输

**修复建议**：
1. 强制 HTTPS：
```python
target_url = f'https://{CLOUD_5004_HOST}:{CLOUD_5004_PORT}/api/smartsheet/write'
```
2. 在 CLOUD_5004_HOST 校验时要求 `https://` 前缀

**严重度**：🟡 P2 - 安全加固项，依赖部署环境。

---

## 八、审计总结

### 8.1 严重度分布

| 严重度 | 数量 | 占比 |
|:------:|:----:|:----:|
| 🔴 P0 | 2 | 18% |
| 🟠 P1 | 8 | 73% |
| 🟡 P2 | 6 | 9%（含 1 个 P2 误判） |

> 注：原文 8 个 + 1 个误判 = 总 16 项（按本节罗列）

### 8.2 问题类别分布

| 类别 | 数量 | 占比 |
|------|:----:|:----:|
| SQL 语法错误 | 1 | 6% |
| SQL 业务逻辑错误 | 3 | 19% |
| SQL 性能问题 | 5 | 31% |
| 索引缺失 | 4 | 25% |
| 事务/并发 | 1 | 6% |
| 文档合规 | 2 | 13% |

### 8.3 优先修复顺序

```
🔴 P0（必须立即修复）
  1. P0-A  CASE WHEN 多值语法错误（生产日报失败）          cloud_relay.py:214-218
  2. P0-B  inventory_monthly 期初数量硬编码 0             cloud_relay.py:489-490

🟠 P1（建议下个迭代修复）
  3. P1-H  _calc_pct 合格率计算错误                       cloud_relay.py:235, 305
  4. P1-A  _q_inventory_weekly N+1 查询                  cloud_relay.py:431-463
  5. P1-B  _q_inventory_alert LEFT JOIN 无日期过滤       cloud_relay.py:500-538
  6. P1-C  _q_inventory_slow_moving 同问题 + NULL 处理  cloud_relay.py:541-581
  7. P1-D  _q_workorder_progress 无 LIMIT/ORDER BY     cloud_relay.py:313-355
  8. P1-E  JSON 函数无容错（防御性）                    cloud_relay.py:322-334
  9. P1-G  _q_inventory_balance 无错误处理              cloud_relay.py:406-428
  10. P1-F  索引迁移脚本补充                              新增 SQL 迁移

🟡 P2（下下个迭代或文档化）
  11. P2-A  WHERE/CASE 字段不一致                       cloud_relay.py:213-225
  12. P2-B  YEARWEEK 参数化                              cloud_relay.py:440
  13. P2-C  LEFT JOIN 实为 INNER JOIN                   cloud_relay.py:441
  14. P2-D  HAVING 引用别名（可移植性）                 cloud_relay.py:518, 560
  15. P2-E  差异率计算语义                                cloud_relay.py:235
  16. P2-F  推送 payload 未加密                          cloud_relay.py:687
```

### 8.4 关键证据清单

| 严重度 | 文件:行号 | 问题 |
|:------:|----------|------|
| 🔴 P0 | cloud_relay.py:214-218 | `CASE HOUR(...) WHEN 6,7,8,...` 语法错误 |
| 🔴 P0 | cloud_relay.py:489-490 | `r['期初数量'] = 0` 硬编码 |
| 🟠 P1 | cloud_relay.py:457-458 | N+1 查询模式 |
| 🟠 P1 | cloud_relay.py:512-513 | LEFT JOIN 无日期范围 |
| 🟠 P1 | cloud_relay.py:235, 305 | `_calc_pct(完成数, 完成数, 100)` |
| 🟠 P1 | cloud_relay.py:336-340 | 无 LIMIT/ORDER BY |
| 🟠 P1 | cloud_relay.py:406-428 | N+1 + 无 try/except |
| 🟡 P2 | cloud_relay.py:74 | `_autocommit=True` 配置 |
| 🟡 P2 | cloud_relay.py:96-98 | 连接池配置 10/2/5 |

---

## 九、审计结论

### 9.1 整体评价

> **核心 SQL 设计存在 2 个 P0 级硬伤**（语法错误 + 业务逻辑错误），导致 9 张表中的 **`production_daily_report` 和 `inventory_monthly_summary` 实际上推送的数据是错误的**。
>
> 即使修复 P0，**P1 级的 8 个性能/正确性问题**也会在数据量增长后逐步暴露。建议本轮修复 P0 + P1-H（合格率 bug），其余列入下个迭代。

### 9.2 文档与代码的一致性

- ✅ R-001 豁免说明在 ARCHITECTURE_v3.6.md:222 明确
- ✅ 9 张表 cron 时间表（v3.6.8 N-1 段落）清晰
- ⚠️ 连接池配置（10/2/5）未在文档中说明
- ⚠️ 索引迁移脚本未覆盖 9 张表涉及的 `process_records.plan_start` 等关键索引
- ⚠️ N+1 查询反模式未在代码注释中标注 TODO

### 9.3 与前两轮审计的衔接

| 前两轮已修复 | 本轮新发现 | 共存 |
|:----:|:----:|:----:|
| D-1 CASE WHEN 边界 ✅ | P0-A CASE WHEN 语法 ❌ | **回归**：业务理解正确但语法错误 |
| D-3 inventory_weekly LIMIT ✅ | P1-A N+1 问题 ❌ | 新发现，前轮未涉及 |
| D-4 substep_recent limit ✅ | P1-G balance 无 try/except ❌ | 关联问题 |
| D-5 R-001 适用范围 ✅ | R-001 边界文档化 ⚠️ | 文档可补强 |

---

**审计员签名**：数据库工程师（第三轮）
**审计日期**：2026-06-24
**下次审计建议**：修复 P0 后立即做"回归审计"，确认生产日报和物料收发存数据正确性。
