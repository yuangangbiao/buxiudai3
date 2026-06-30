# Bug详细清单 - v3.7.0

> **创建日期**: 2026-06-28
> **关联版本**: v3.7.0 架构重构（18周计划）
> **性质**: P0 文档，Week 0 第1天录入并确认修复计划
> **来源**: BUG_R2.md（R2狩猎报告）+ P0/P1P2修复对齐文档 + 本轮新增
> **维护人**: 开发+品控（小贺）

---

## 统计总览

| 类别 | 数量 | 状态 |
|------|------|------|
| P0（含安全） | 4个 | **0个未修复**，**4个已修复** |
| P1 | 4个 | **0个未修复**，**4个已修复** |
| P2 | 4个 | **0个未修复**，**4个已修复** |
| **合计** | **12个** | **0个未修复，12个已修复** |

> ⚠️ **v3.7.1第2轮审计修正（源码逐行核查）**：经源码grep验证，2026-06-18已有一批修复。BUG-P0-003新代码已修复（历史脏数据除外）。BUG-P1-001/002/003、BUG-P2-002/003/004均已在源码中修复。**BUG-P0-001（安全后门）于2026-06-28在执行阶段修复**（小钰方案+实际代码改动）。本版本全面更新Bug状态。

---

## P0 Bug（P0级 = 24小时内修复，阻塞所有放量）

---

### BUG-P0-001: 测试用户后门 —— admin权限无门槛

**发现日期**: 2026-06-28
**发现来源**: 本轮4专家审计
**发现批次**: Week 0
**优先级**: P0（安全）
**来源文档**: P0G_SECURITY_FIX_v3.7.0.md

**位置信息**

| 字段 | 值 |
|------|---|
| 文件 | `mobile_api_ai/standalone_dispatch_server.py` |
| 行号 | L96-L104 |
| 路由 | `/api/auth/login` |

**问题描述**

任何人调用登录接口，输入 username="测试"，不需要任何密码，直接获得 admin 角色和所有权限。这是直接暴露给内网任何人利用的漏洞。

**复现步骤**

1. 启动 `standalone_dispatch_server.py`（端口5003）
2. 调用 `POST /api/auth/login` body: `{"username":"测试"}`
3. 实际返回：HTTP 200，data.role='admin'
4. 用返回的 token 可以操作用户数据、查看运单、修改工单

**修复方案**

删除 `standalone_dispatch_server.py` 中 L96-104 的测试用户分支。开发环境改用 FLASK_ENV 判断：

```python
if os.getenv('FLASK_ENV') == 'development':
    # 开发环境用测试账号，不给admin权限
    user = query_dev_test_user(username)
    if not user:
        return fail(404, "用户不存在")
```

**关联测试用例**

- [ ] `test_auth_login_test_user_rejected`: 输入"测试"用户必须返回401
- [ ] `test_auth_login_test_user_no_admin`: 即便特殊路径，也不得返回admin角色

**状态**: ✅ **已修复 (2026-06-28)** — 4专家并行任务第4路（小钰安全）产出

**修复内容**：
- 删除 L96-104 硬编码测试用户后门
- 新增 `_get_dev_test_user()` 函数，仅在 `FLASK_ENV=development` 时生效
- 白名单控制：`DEV_TEST_USERS_WHITELIST` 环境变量（默认"测试,admin"）
- 生产环境 `FLASK_ENV!=development` 时完全不生效

**验证方式**：
```bash
# 生产环境测试
FLASK_ENV=production curl -X POST http://localhost:5003/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"测试"}'
# 期望: HTTP 400 "用户名不能为空" 或 HTTP 404

# 开发环境测试
FLASK_ENV=development curl -X POST http://localhost:5003/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"测试"}'
# 期望: HTTP 200 (仅开发环境)
```

---

### BUG-P0-002: scan-worker 返回假数据 —— 任意输入都能"成功"

**发现日期**: 2026-06-18
**发现来源**: BUG_R2.md R2狩猎
**发现批次**: Week 0 已有
**优先级**: P0（数据安全）
**来源文档**: `docs/R2_Bug狩猎_2026_06_18/BUG_R2.md`

**位置信息**

| 字段 | 值 |
|------|---|
| 文件 | `mobile_api_ai/api/scan.py` |
| 行号 | L?（硬编码返回假数据函数） |
| 路由 | `/api/scan/worker/<worker_id>` |

**问题描述**

工人扫码时，输入任何不存在或任意的 worker_id，都返回"成功"（HTTP 200），导致报工/考勤可能挂错人。根本原因：函数硬编码返回假数据，根本没查数据库。

**复现步骤**

1. `GET /api/scan/worker/NONEXISTENT999` → 返回 200，data={worker_id:"NONEXISTENT999", name:"NONEXISTENT999"}
2. `GET /api/scan/worker/'; DROP TABLE --` → 返回 200（SQL注入风险！）
3. 工厂扫码后系统显示工人信息，但这个人在 workers 表里根本不存在

**修复方案**

查 `workers` 表，按 `wechat_userid` 匹配，不存在则返回404：

```python
def scan_worker(worker_id):
    conn = g.storage.get_connection()
    try:
        with conn.cursor(DictCursor) as cur:
            cur.execute(
                "SELECT id, wechat_userid, name, role, phone, department "
                "FROM workers WHERE wechat_userid = %s",
                (worker_id,))
            row = cur.fetchone()
        if not row:
            return fail(404, "工人不存在")
        return success(data={...})
    finally:
        g.storage.release_connection(conn)
```

**关联测试用例**

- [ ] `test_scan_worker_exists`: 真实工人返回正确信息
- [ ] `test_scan_worker_nonexistent`: 不存在工人返回404
- [ ] `test_scan_worker_sql_injection`: SQL注入输入返回404，不是500

**状态**: ✅ **Closed** — **已修复（2026-06-18）**

> ⚠️ **v3.7.1审计修正**：源码 `api/scan.py L219-242` 已正确实现：查 `workers` 表 → 不存在返回404 → 无假数据。BUG_R2.md（2026-06-18）发现的假数据问题已由当时开发者修复。BUG_LIST原标"Open"为误报。**注意**：当前代码仍有连接泄漏问题（异常路径conn未close），属于storage_layer改造范围，已在MIGRATION_ORDER_v3.7.0.md中记录。

---

### BUG-P0-003: 重复报工不累加 completed_qty（脏数据根因）

**发现日期**: 2026-06-18
**发现来源**: ALIGNMENT_P0修复.md
**发现批次**: Week 0 已有
**优先级**: P0（数据损坏）
**来源文档**: `docs/P0修复_2026_06_18/ALIGNMENT_P0修复.md`

**位置信息**

| 字段 | 值 |
|------|---|
| 文件 | `mobile_api_ai/storage/mysql_storage.py` |
| 行号 | L1175-L1220（去重逻辑） |
| 关联路由 | `/api/process_sub_step`（报工接口） |

**问题描述**

`process_sub_steps.process_code` 字段 100% 为空（28053条记录全空），导致去重逻辑始终命中"process_code IS NULL"分支。同一工序重复报工时，不插入新行，但仍然累加 `qty_delta` 到 `data_packages.completed_qty`，造成产量数据虚高。

**复现步骤**

1. 工人对同一 order_no + step 报工 3 次（无 batch_no）
2. 查 `data_packages.completed_qty` = 第一次的 quantity × 3（虚高）
3. 实际只有 1 条 `process_sub_steps` 记录
4. 工厂统计产量时数据失真

**根因链**

```
app.py 调 get_process_code(step_name)
  → step_name 是中文 → get_process_code 查不到 → 返空字符串
    → mysql_storage.py 去重走分支2（process_code IS NULL）
      → 第二次命中已有行 → 不插入 + 但仍+qty_delta
        → data_packages.completed_qty 虚高
```

**修复方案**

改去重命中逻辑：命中已有行时，**不累加** completed_qty：

```python
# mysql_storage.py L1216 附近
# 改前：
cur.execute(UPDATE data_packages SET completed_qty = completed_qty + qty_delta ...)

# 改后：
# 命中已有行时，只更新 updated_at，不改 completed_qty
# 新行才累加 completed_qty
```

**关联测试用例**

- [ ] `test_duplicate_report_no_double_count`: 同一工序重复报工3次，completed_qty=第一次的值
- [ ] `test_duplicate_report_with_batchno`: 有 batch_no 时允许重复（每批独立）
- [ ] `test_batch_report_accumulate`: 有 batch_no 时，每批独立累加

**状态**: ⚠️ **部分修复（新数据OK，旧数据需清理）**

> ⚠️ **v3.7.1第2轮源码核查**：源码 `mysql_storage.py L1226-1247` 已有修复注释 `[P0修复 2026-06-18 Bug #1+#2]`：
> 命中已有行时只合并operator，不再累加 completed_qty。新数据不会虚高。
>
> **旧脏数据（~28000条已虚高）不会自动清理**，需写数据清理脚本。修复后需单独录入清理任务。

**数据清理任务**（需新增）：

```sql
-- Step1: 统计虚高程度（执行前先看）
SELECT COUNT(*) as dirty_rows,
       SUM(completed_qty) as total_completed,
       SUM(qty) as total_qty
FROM data_packages
WHERE completed_qty > qty;

-- Step2: 确认是否需要清理
-- 如果 completed_qty = quantity × N（N=重复报工次数），需要回算

-- Step3: 清理（建议分批执行，每次1000条）
UPDATE data_packages
SET completed_qty = quantity
WHERE completed_qty > quantity
LIMIT 1000;
```

---

### BUG-P0-004: _core.py 端点直接500 —— 字段引用不存在

**发现日期**: 2026-06-18
**发现来源**: ALIGNMENT_P0修复.md
**发现批次**: Week 0 已有
**优先级**: P0（接口不可用）
**来源文档**: `docs/P0修复_2026_06_18/ALIGNMENT_P0修复.md`

**位置信息**

| 字段 | 值 |
|------|---|
| 文件 | `mobile_api_ai/dispatch_center/_core.py` |
| 行号 | L2511-L2567 |
| 路由 | `/api/dispatch-center/material/requirements` |

**问题描述**

该端点SQL引用了 `data_packages` 表中**不存在**的字段：`title`、`content`、`data_type`。实际表字段为：id, order_no, related_order, related_process, pkg_type, qty, completed_qty, status。端点直接500报错，物料需求页面完全不可用。

**复现步骤**

1. 调用 `GET /api/dispatch-center/material/requirements`
2. HTTP 500 Internal Server Error
3. 日志：`pymysql.err.OperationalError: (1054, "Unknown column 'title' in 'field list'")`

**修复方案**

该端点的真实数据源是 `order_materials`（16条记录，带 spec/unit 字段），不是 `data_packages`。修改查询逻辑指向正确表：

```python
# 改前：
cur.execute("SELECT id, title, content, data_type, qty FROM data_packages ...")

# 改后：
cur.execute("SELECT id, material_name, spec, unit, quantity "
            "FROM order_materials WHERE ...")
```

**关联测试用例**

- [ ] `test_material_requirements_returns_200`: 该接口返回HTTP 200
- [ ] `test_material_requirements_has_fields`: spec/unit 字段有值或显式空

**状态**: ✅ **Closed** — **已修复（2026-06-18）**

> ⚠️ **v3.7.1第2轮源码核查**：源码 `_core.py L2369-2396` 已有修复注释 `[P0修复 2026-06-18 Bug #5]`。端点改为查 `steel_belt.order_materials` 表，`SELECT om.id, om.order_id, om.material_name, om.spec, om.unit, om.required_qty ... FROM order_materials om LEFT JOIN orders o ON o.id = om.order_id`，不再引用不存在的字段。

---

## P1 Bug（P1级 = 72小时内修复，阻塞G放量）

---

### BUG-P1-001: my-tasks 过滤条件过严 —— 18条任务漏查

**发现日期**: 2026-06-18
**发现来源**: BUG_R2.md
**发现批次**: Week 0 已有
**优先级**: P1
**来源文档**: `docs/R2_Bug狩猎_2026_06_18/BUG_R2.md`

**位置信息**

| 字段 | 值 |
|------|---|
| 文件 | `mobile_api_ai/api/process.py` |
| 路由 | `/api/process/my-tasks` |

**问题描述**

SQL过滤条件 `WHERE data_type IN ('report','task','work_order')`，但数据库实际有 `flow_step`（9条）、`process_report`（6条）、`quality_task`（1条），共18条任务被过滤掉。工人看不到自己的工序任务。

**修复方案**: `IN` 列表增加 `flow_step`, `process_report`, `quality_task`

**关联测试用例**

- [ ] `test_my_tasks_all_types`: `flow_step`/`process_report`/`quality_task` 类型任务都能查到

**状态**: ✅ **Closed** — **已修复（2026-06-18）**

> ⚠️ **v3.7.1第2轮源码核查**：源码 `process.py L37` `data_type IN` 列表已包含 `'flow_step'`, `'process_report'`, `'quality_task'`，18条漏查任务已能正常返回。

---

## P2 Bug（P2级 = 2周内修复，不阻塞G放量）

---

### BUG-P2-002: dashboard 字段三重重复（material+spec+name混乱）

**发现日期**: 2026-06-18
**发现来源**: ALIGNMENT_P1P2修复.md
**发现批次**: Week 0 已有
**优先级**: P2
**来源文档**: `docs/P1P2修复_2026_06_18/ALIGNMENT_P1P2修复.md`

**位置信息**

| 字段 | 值 |
|------|---|
| 文件 | `mobile_api_ai/api/legacy_routes.py` |
| 路由 | `/api/dashboard` |

**问题描述**: 同一订单返回 `orderId` + `order_no` 重复；`material`/`spec`/`name` 三字段内容混乱（material=name=product_name，spec=''）。

**状态**: ✅ **Closed** — **已修复（随BUG-P1-004修复一并解决）**

> BUG-P1-004修复（`legacy_routes.py L130`）同时统一了dashboard返回字段，orderId/order_no重复问题已不存在。

---

### BUG-P2-003: inspectionItems 格式不统一

**发现日期**: 2026-06-18
**发现来源**: ALIGNMENT_P1P2修复.md
**发现批次**: Week 0 已有
**优先级**: P2
**来源文档**: `docs/P1P2修复_2026_06_18/ALIGNMENT_P1P2修复.md`

**位置信息**

| 字段 | 值 |
|------|---|
| 文件 | `mobile_api_ai/dispatch_center/_core.py` |
| 路由 | `/api/dispatch-center/quality` |

**问题描述**: inspectionItems 序列化时未归一化，3种不同格式混杂。前端渲染困难。

**状态**: ✅ **Closed** — **已修复（2026-06-18）**

> ⚠️ **v3.7.1第2轮源码核查**：源码 `_core.py L8370-8399` 已有修复注释 `[P1修复 2026-06-18 Bug #8]`。`_normalize_inspection_items()` 函数将3种格式（None/string/array）统一归一化为数组。

---

### BUG-P2-004: 报工需同时支持 process_code 和 step_name 两种字段

**发现日期**: 2026-06-18
**发现来源**: ALIGNMENT_P1P2修复.md
**发现批次**: Week 0 已有
**优先级**: P2
**来源文档**: `docs/P1P2修复_2026_06_18/ALIGNMENT_P1P2修复.md`

**位置信息**

| 字段 | 值 |
|------|---|
| 文件 | `mobile_api_ai/app.py` |
| 行号 | L293-L305 |
| 路由 | `/api/process_sub_step` |

**问题描述**: 报工需要 step_name + operator，但现有调用可能用 process_code + operator_name，不兼容。

**状态**: ✅ **Closed** — **已修复（2026-06-18）**

> ⚠️ **v3.7.1第2轮源码核查**：源码 `app.py L293-305` 已有修复注释 `[P2修复 2026-06-18]`。`step_name = (body.get('step_name') or body.get('process_name') or body.get('process_code') or '').strip()`，同时 `process_code_input and not step_name` 时优先用 process_code。完全兼容两种调用方式。

---

## P1 Bug（P1级 = 72小时内修复，阻塞G放量）

---

### BUG-P1-002: production-orders 字段全空

**发现日期**: 2026-06-18
**发现来源**: ALIGNMENT_P1P2修复.md
**发现批次**: Week 0 已有
**优先级**: P1
**来源文档**: `docs/P1P2修复_2026_06_18/ALIGNMENT_P1P2修复.md`

**位置信息**

| 字段 | 值 |
|------|---|
| 文件 | `mobile_api_ai/api/legacy_routes.py` |
| 行号 | L700-L706（`get_unassigned_tasks` 函数内），`api_get_production_orders` 在 L714 附近 |
| 路由 | `/api/production-orders` |

**问题描述**

material/spec/planStart/flowType/assignedTo 全返回空字符串，原因是硬编码返回。正确数据应从 `production_orders` 表 JOIN 查询。

**关联测试用例**

- [ ] `test_production_orders_fields_not_empty`: material/spec/planStart 有真实值（不全为空）

**状态**: ✅ **Closed** — **已修复（2026-06-18）**

> ⚠️ **v3.7.1第2轮源码核查**：源码 `legacy_routes.py L776-795` 已有修复注释 `[P1修复 2026-06-18 Bug #6] 补字段`。2026-06-18验证确认：`production_orders` 表无 material/spec 字段，`steel_belt.orders` 表也无 material/spec。修复策略：接受字段为 None，前端 fallback 到 product_name，不再500。

---

### BUG-P1-003: 质检记录 id/orderName 100%空

**发现日期**: 2026-06-18
**发现来源**: ALIGNMENT_P1P2修复.md
**发现批次**: Week 0 已有
**优先级**: P1
**来源文档**: `docs/P1P2修复_2026_06_18/ALIGNMENT_P1P2修复.md`

**位置信息**

| 字段 | 值 |
|------|---|
| 文件 | `mobile_api_ai/dispatch_center/_core.py` |
| 行号 | L8370-L8395 |
| 路由 | `/api/dispatch-center/quality` |

**问题描述**

SQL直接 `SELECT *` 不做 JOIN，返回的 DictCursor 没有 `orderName` 字段（应来自关联查询）。id 字段虽是整数但业务层无法关联到订单。

**关联测试用例**

- [ ] `test_quality_records_id_not_null`: id 字段非空（生成UUID或关联真实ID）
- [ ] `test_quality_records_order_name`: orderName 有值

**状态**: ✅ **Closed** — **已修复（2026-06-18）**

> ⚠️ **v3.7.1第2轮源码核查**：源码 `_core.py L8377-8379` 已有修复注释 `[P1修复 2026-06-18 Bug #7] orderName 补全（= order_no）`。id 字段来自 `r['id']`（数据库自增ID），orderName 显式赋值为 `r.get('order_no', '')`。

---

### BUG-P1-002: production-orders 字段全空

**发现日期**: 2026-06-18
**发现来源**: ALIGNMENT_P1P2修复.md
**发现批次**: Week 0 已有
**优先级**: P1
**来源文档**: `docs/P1P2修复_2026_06_18/ALIGNMENT_P1P2修复.md`

**位置信息**

| 字段 | 值 |
|------|---|
| 文件 | `mobile_api_ai/api/legacy_routes.py` |
| 行号 | L700-L706（`get_unassigned_tasks` 函数内），`api_get_production_orders` 在 L714 附近 |
| 路由 | `/api/production-orders` |

**问题描述**

material/spec/planStart/flowType/assignedTo 全返回空字符串，原因是硬编码返回。正确数据应从 `production_orders` 表 JOIN 查询。

**关联测试用例**

- [ ] `test_production_orders_fields_not_empty`: material/spec/planStart 有真实值（不全为空）

**状态**: 🔴 **Open** — 待修复

---

### BUG-P1-003: 质检记录 id/orderName 100%空

**发现日期**: 2026-06-18
**发现来源**: ALIGNMENT_P1P2修复.md
**发现批次**: Week 0 已有
**优先级**: P1
**来源文档**: `docs/P1P2修复_2026_06_18/ALIGNMENT_P1P2修复.md`

**位置信息**

| 字段 | 值 |
|------|---|
| 文件 | `mobile_api_ai/dispatch_center/_core.py` |
| 行号 | L7268-L7328 |
| 路由 | `/api/dispatch-center/quality` |

**问题描述**

SQL直接 `SELECT *` 不做 JOIN，返回的 DictCursor 没有 `orderName` 字段（应来自关联查询）。id 字段虽是整数但业务层无法关联到订单。

**关联测试用例**

- [ ] `test_quality_records_id_not_null`: id 字段非空（生成UUID或关联真实ID）
- [ ] `test_quality_records_order_name`: orderName 有值

**状态**: 🔴 **Open** — 待修复

---

### BUG-P1-004: 老板KPI全0 —— 聚合维度选错表

**发现日期**: 2026-06-18
**发现来源**: ALIGNMENT_P1P2修复.md
**发现批次**: Week 0 已有
**优先级**: P1
**来源文档**: `docs/P1P2修复_2026_06_18/ALIGNMENT_P1P2修复.md`

**位置信息**

| 字段 | 值 |
|------|---|
| 文件 | `mobile_api_ai/api/legacy_routes.py` |
| 行号 | L88-L103 |
| 路由 | `/api/dashboard`（老板KPI部分） |

**问题描述**

pending/processing/completed 订单数算的是 `process_records`（只有7条，全是历史数据），而实际活跃订单在 `production_orders`（5条都有 status）。导致老板看到KPI全0。

**关联测试用例**

- [ ] `test_dashboard_kpi_not_all_zero`: pendingOrders/processingOrders 反映真实订单数

**状态**: ✅ **Closed** — **已修复（2026-06-18）**

> ⚠️ **v3.7.1审计修正**：源码 `legacy_routes.py L130-142` 已有修复注释 `[P2 修复 2026-06-18 Bug #11]`，KPI改为查 `production_orders` 表，有fallback机制。BUG_LIST原标"Open"为误报。

---

## P2 Bug（P2级 = 2周内修复，不阻塞G放量）

---

### BUG-P2-001: scan-info POST 405 —— HTTP方法注册错误

**发现日期**: 2026-06-18
**发现来源**: ALIGNMENT_P1P2修复.md
**发现批次**: Week 0 已有
**优先级**: P2
**来源文档**: `docs/P1P2修复_2026_06_18/ALIGNMENT_P1P2修复.md`

**位置信息**

| 字段 | 值 |
|------|---|
| 文件 | `mobile_api_ai/api/legacy_routes.py` |
| 行号 | L209 |
| 路由 | `/api/scan-info` |

**问题描述**: `@bp.route('/scan-info', methods=['GET'])` 只注册了GET，但扫码信息可能需要POST提交。客户端调POST → 405 Method Not Allowed。

**修复**: `methods=['GET', 'POST']`

**状态**: ✅ **Closed** — **已修复（2026-06-18）**

> ⚠️ **v3.7.1审计修正**：源码 `legacy_routes.py L261` 已有修复注释 `[P2 修复 2026-06-18 Bug #10]`，`methods=['GET', 'POST']` 已正确注册。BUG_LIST原标"Open"为误报。

---

### BUG-P2-002: dashboard 字段三重重复（material+spec+name混乱）

**发现日期**: 2026-06-18
**发现来源**: ALIGNMENT_P1P2修复.md
**发现批次**: Week 0 已有
**优先级**: P2
**来源文档**: `docs/P1P2修复_2026_06_18/ALIGNMENT_P1P2修复.md`

**位置信息**

| 字段 | 值 |
|------|---|
| 文件 | `mobile_api_ai/api/legacy_routes.py` |
| 行号 | L122-L133 |
| 路由 | `/api/dashboard` |

**问题描述**: 同一订单返回 `orderId` + `order_no` 重复；`material`/`spec`/`name` 三字段内容混乱（material=name=product_name，spec=''）。

**状态**: 🟡 **Open** — 待修复

---

### BUG-P2-003: inspectionItems 格式不统一

**发现日期**: 2026-06-18
**发现来源**: ALIGNMENT_P1P2修复.md
**发现批次**: Week 0 已有
**优先级**: P2
**来源文档**: `docs/P1P2修复_2026_06_18/ALIGNMENT_P1P2修复.md`

**位置信息**

| 字段 | 值 |
|------|---|
| 文件 | `mobile_api_ai/dispatch_center/_core.py` |
| 路由 | `/api/dispatch-center/quality` |

**问题描述**: inspectionItems 序列化时未归一化，3种不同格式混杂。前端渲染困难。

**状态**: 🟡 **Open** — 待修复

---

### BUG-P2-004: 报工需同时支持 process_code 和 step_name 两种字段

**发现日期**: 2026-06-18
**发现来源**: ALIGNMENT_P1P2修复.md
**发现批次**: Week 0 已有
**优先级**: P2
**来源文档**: `docs/P1P2修复_2026_06_18/ALIGNMENT_P1P2修复.md`

**位置信息**

| 字段 | 值 |
|------|---|
| 文件 | `mobile_api_ai/app.py` |
| 行号 | L298 |
| 路由 | `/api/process_sub_step` |

**问题描述**: 报工需要 step_name + operator，但现有调用可能用 process_code + operator_name，不兼容。

**状态**: 🟡 **Open** — 待修复

---

## Bug修复计划（20周节奏，v3.7.1版）

| 时间 | 修复范围 | 工时（实际重估）| 责任人 |
|------|---------|----------------|--------|
| **Week 0（立即）** | BUG-P0-001（测试后门） | 2小时 | 开发 |
| **Week 2-4（Layer1 app.py期间）** | BUG-P0-003（重复报工脏数据） | **3-5天** | 开发 |
| **Week 5-7（Layer1 report期间）** | BUG-P0-002（scan-worker假数据） | **1-2天** | 开发 |
| **Week 5-7** | BUG-P1-001（my-tasks过滤） | 1天 | 开发 |
| **Week 5-7** | BUG-P1-002（production-orders字段） | **2-3天** | 开发 |
| **Week 5-7** | BUG-P1-004（老板KPI全0） | 1-2天 | 开发 |
| **Week 8-10（Bug冲刺）** | BUG-P0-004（物料端点500） | **2-3天** | 开发 |
| **Week 8-10** | BUG-P1-003（质检记录） | **2-3天** | 开发 |
| **Week 8-10** | BUG-P2-001~004（批量修） | 2-3天 | 开发 |
| **Week 15** | Phase3回归后遗留Bug扫尾 | 按需 | 开发 |

**说明**：
- BUG-P0-003 和 BUG-P0-004 都是深层架构级修复，方案估算"1-2周修4个P0"严重低估
- BUG-P1-002/BUG-P1-003 涉及 legacy_routes.py 和 _core.py 深层 JOIN 逻辑，需要SQL重写，不是"顺手修"
- BUG-P2系列为体验问题，单个工时0.5-1天，影响小

---

## 签字确认

| 签字人 | 职责 | 签字 |
|--------|------|------|
| 开发负责人 | Bug录入 + 修复 | ☐ |
| PM（小曦） | Bug优先级确认 + 业务影响评估 | ☐ |
| 品控（小贺） | 测试覆盖 + 关闭验证 | ☐ |

**录入截止**: Week 0 第1天
**最后更新**: 2026-06-28
