# 5008 移动端报工系统架构文档 v1.0

> **文档版本**：v1.0
> **更新日期**：2026-06-24
> **入口文件**：`mobile_api_ai/app.py`
> **服务端口**：5008
> **核心职责**：工序报工、质检、维修、外协、物料采购、排产调度、移动端登录
> **数据库**：MySQL `container_center`（主）+ `steel_belt`（同步副本）

---

## 一、架构总览

### 1.1 系统定位

5008 是**移动端报工系统的核心服务**，面向车间工人和调度员，提供工序报工、质检、维修、外协、物料采购、排产调度等全流程移动端操作入口。

**架构特征**：
- 单文件入口（`app.py` ≈ 2100 行）内嵌大量直接路由（inline routes）
- 配合 Blueprint 蓝图组织 API 层（`mobile_api_ai/api/`）
- 连接 `container_center` + `steel_belt` 双库
- 是 5003 调度中心的**触发端和数据操作端**，而非调度逻辑端

### 1.2 六层架构

```
┌──────────────────────────────────────────────────────────────────────┐
│                    mobile_api_ai/app.py (Flask, 5008)                │
│  ┌──────────────────┬──────────────────────────────────────────┐   │
│  │  登录认证        │ /api/login (JWT token)                    │   │
│  │  健康检查        │ /health                                    │   │
│  │  静态文件       │ /mobile_login.html                          │   │
│  └──────────────────┴──────────────────────────────────────────┘   │
│                              │                                       │
│         ┌────────────────────┴────────────────────┐                 │
│         │         app.py 内联路由 (~2100 行)       │                 │
│         │  报工提交 / 撤回 / 修改 / 质检 / 物料   │                 │
│         │  维修 / 外协 / 排产 / 统一任务查询       │                 │
│         │  容器中心 SSOT 代理 / 同步桥接           │                 │
│         └────────────────────┬────────────────────┘                 │
│                              │                                       │
│         ┌────────────────────┴────────────────────┐                 │
│         │           Blueprint 蓝图层                │                 │
│         │  auth | scan | process | quality | msg  │                 │
│         │  approval | health | qi | metrics |     │                 │
│         │  stats | ai | cost | reports | legacy   │                 │
│         │  config_center | dispatch_center | wecom │                 │
│         │  api_v1 (url_prefix=/api/v1)             │                 │
│         │  inventory_external                       │                 │
│         └────────────────────┬────────────────────┘                 │
│                              │                                       │
│         ┌────────────────────┴────────────────────┐                 │
│         │         桥接层 bridge/                  │                 │
│         │  dispatch_center_sync.py (→ 5003)      │                 │
│         │  sync_client.py                         │                 │
│         └────────────────────┬────────────────────┘                 │
│                              │                                       │
│         ┌────────────────────┴────────────────────┐                 │
│         │         存储层 Storage                   │                 │
│         │  MySQLStorage (连接池单例, app.py L58) │                 │
│         │  container_center_v5.ContainerCenter     │                 │
│         │  db.steelbelt_pool (steel_belt DB)    │                 │
│         └────────────────────┬────────────────────┘                 │
│                              │                                       │
│         ┌────────────────────┴────────────────────┐                 │
│         │              MySQL                       │                 │
│         │  container_center (主库)                │                 │
│         │  steel_belt     (同步副本)              │                 │
│         └─────────────────────────────────────────┘                 │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 二、入口文件：app.py 结构

> `app.py` ≈ 2100 行，采用**单文件内嵌路由 + 蓝图注册**的混合架构。

### 2.1 启动流程（L47-68）

```python
def create_app():
    app = Flask(__name__)
    # 1. 存储单例初始化（MySQLStorage 连接池）
    _app_storage = _get_storage()  # L58-60: lazy init 单例
    # 2. CORS 初始化
    init_cors(app, default_origins='...')
    # 3. 限流器初始化
    limiter.init_app(app)
    # 4. 前端 JS 语法检查（启动校验）
    _validate_frontend_js()
    ...
```

### 2.2 app.py 内联路由分段

| 行号范围 | 功能 | 说明 |
|---------|------|------|
| 104-158 | 登录认证 | `/mobile_login.html` `/api/login`（JWT token 颁发）|
| 222-329 | 容器中心 SSOT 代理 | `/api/orders/full-status`（retry 2次 + fallback）|
| 331-477 | 工序任务汇总 | `/api/all-process-tasks`（手机端"工序任务"数据源）|
| 544-571 | 工序任务详情 | `/api/process-tasks/by-order/<order_no>` |
| 574-698 | **报工提交** | `/api/process_sub_step`（含幂等拦截 + 5003 同步 + WeChat 通知）|
| 727-800 | 报工撤回 | `/api/process_sub_step/withdraw` |
| 803-944 | **调度中心·报工记录管理** | `/api/report_record/list/update/withdraw/history_full` |
| 1041-1282 | **调度中心·质检记录管理** | `/api/quality_record/list/update/withdraw/history_full` |
| 1285-1493 | **调度中心·物料记录管理** | `/api/material_record/list/update/withdraw/history_full` |
| 1495-1614 | **调度中心·外协记录管理** | `/api/outsource_record/list/update/withdraw/history_full` |
| 1616-1739 | **调度中心·维修记录管理** | `/api/repair_record/list/create/update/withdraw` |
| 1741-1859 | **调度中心·排产记录管理** | `/api/schedule_record/list/update/withdraw/history_full` |
| 1990-2030 | 统一任务分流 | `/api/tasks`（T5 迁移后 UNION 查 5 表）|
| 2031-？ | 物料任务操作 | `/api/material_flow/*`（物料流程 API）|

### 2.3 app.py 与蓝图的职责划分

| 归属 | 特点 | 典型功能 |
|------|------|---------|
| **app.py 内联** | 直接路由，无需蓝图注册 | 报工 CRUD（需要事务控制）、SSOT 代理、统一查询 |
| **Blueprint 蓝图** | 独立模块，可插拔 | 认证、扫码、审批、AI、消息、WeCom、调度中心、排产 |

---

## 三、蓝图路由架构

### 3.1 蓝图注册顺序（app.py L162-1879）

```python
# 已注册的蓝图（按顺序）
auth.bp           # 认证
scan.bp           # 扫码
process.bp       # 工序
quality.bp        # 质检
message.bp        # 消息
approval.bp        # 审批
health.bp         # 健康检查
qi_bp             # 质检巡查
metrics_bp        # 监控指标
stats.bp          # 统计分析（可选，跳过不报错）
ai.bp             # AI 智能（可选，跳过不报错）
cost.bp           # 成本（可选，跳过不报错）
reports.bp        # 报表（可选，跳过不报错）
legacy_bp         # 遗留路由（兼容晨圣旧版前端）
inventory_external_bp  # 库存防腐层
schedule_bp        # 排产路由
workorder_bp      # 工单路由
dispatch_center_bp # 调度中心核心
wecom_bp          # 企业微信认证
api_v1_bp         # API v1（url_prefix=/api/v1）
```

### 3.2 蓝图 URL 前缀汇总

| 蓝图 | URL 前缀 | 主要端点 |
|------|---------|---------|
| `auth.bp` | —（无前缀）| `/api/login` `/api/logout` |
| `scan.bp` | `/api/scan` | `/api/scan/task` `/api/scan/test/create-sample` |
| `process.bp` | `/api/process` | `/api/process/my-tasks` |
| `quality.bp` | `/api/quality` | `/api/quality/list` `/api/quality/<int>/create` |
| `message.bp` | `/api/message` | `/api/message/list` `/api/message/unread-count` |
| `approval.bp` | `/api/approval` | `/api/approval/pending` `/api/approval/<id>/approve` |
| `health.bp` | — | `/health` |
| `qi_bp` | — | 质检巡查相关 |
| `metrics_bp` | `/api/metrics` | `/api/metrics/stats` `/api/metrics/health` |
| `ai.bp` | `/api/ai` | `/api/ai/speech-to-report` `/api/ai/image-analysis` `/api/ai/chat` |
| `legacy_bp` | **无前缀** | `/api/dashboard` `/api/scan-info` `/api/attendance` |
| `inventory_external_bp` | `/inventory` | 库存防腐层（供桌面端 HTTP 调用）|
| `schedule_bp` | `/api/schedule` | `/api/schedule/publish` `/api/schedule/notify` 等 |
| `dispatch_center_bp` | `/api/dispatch-center` | 调度中心核心 API |
| `wecom_bp` | — | 企业微信认证 |
| `api_v1_bp` | `/api/v1` | v1 版本化 API |

### 3.3 可选蓝图容错注册

```python
# 以下蓝图注册时使用 try/except，若未实现则跳过并记录 warning
try:
    from mobile_api_ai.api.stats import bp as stats_bp
    app.register_blueprint(stats_bp)
except (ImportError, AttributeError) as e:
    logger.warning(f"[App] 蓝图 stats 注册跳过: {e}")
```

| 蓝图 | 状态 | 说明 |
|------|------|------|
| `stats` | 可选 | 统计分析，未实现时跳过 |
| `ai` | 可选 | AI 智能，未实现时跳过 |
| `cost` | 可选 | 成本核算，未实现时跳过 |
| `reports` | 可选 | 报表，未实现时跳过 |

---

## 四、存储层架构

### 4.1 连接池架构

```
┌──────────────────────────────────────────┐
│     app.py L58: MySQLStorage()          │
│     (连接池单例，lazy init)              │
│     _storage_pool = None                 │
│     _get_storage() → singleton           │
└──────────┬───────────────────────────────┘
           │
  ┌────────┴────────┐
  │                 │
  ▼                 ▼
container_center   steel_belt
  (主库)           (同步副本)
  process_sub_steps  orders
  quality_records   quality_records
  material_records  process_records
  outsource_records
  repair_records
  schedule_records
  dispatch_cache
```

### 4.2 多存储访问路径

| 路径 | 数据库 | 用途 |
|------|--------|------|
| `_get_storage()` → `MySQLStorage` | `container_center` | 主流业务读写 |
| `_get_storage()._pool.connection()` | `container_center` | 直接连接池操作（事务控制）|
| `db.steelbelt_pool.cursor()` | `steel_belt` | 订单存在性校验（app.py L611-617）|
| `container_center_v5.ContainerCenter` | `container_center` | v5 兼容查询（工序聚合、状态计算）|
| `core.db_compat.get_conn()` | `steel_belt` | SSOT fallback 本地查询 |

### 4.3 事务控制模式

app.py 中的事务控制示例（报工撤回，L741-749）：

```python
conn = storage._pool.connection()
try:
    cur = conn.cursor()
    cur.execute("SELECT * FROM process_sub_steps WHERE id=%s FOR UPDATE", (sub_step_id,))
    # ...
    cur.execute("COMMIT")
finally:
    conn.close()
```

**特征**：
- 使用 `storage._pool.connection()` 获取连接
- `FOR UPDATE` 行级锁防止并发冲突
- `finally` 确保连接归还
- 部分操作使用 `START TRANSACTION` / `COMMIT` 显式控制

---

## 五、核心业务逻辑

### 5.1 报工流程（/api/process_sub_step）

```
手机端 POST /api/process_sub_step
    │
    ├─① 订单存在性校验（steel_belt.orders）
    │       db.steelbelt_pool.cursor()
    │
    ├─② 幂等拦截（batch_no 去重）
    │       storage.fetch_all(... WHERE batch_no=...)
    │       → 已存在则返回 idempotent: True
    │
    ├─③ 写入 process_sub_steps
    │       MySQLStorage.save_process_sub_step_with_pkg_update()
    │       事务：主表 + package 更新
    │
    ├─④ 同步到 5003 调度中心
    │       bridge.dispatch_center_sync.send_sub_step_report()
    │
    └─⑤ 通知 5003 推送微信
            POST http://127.0.0.1:5003/api/dispatch-center/report-submitted
            → WeChatNotifier → 车间工人
```

### 5.2 调度中心·报工记录管理（/api/report_record/*）

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/report_record/list` | GET | 报工记录列表（支持订单/工序/操作人/日期筛选 + 分页）|
| `/api/report_record/update` | POST | 调度员修改报工记录（含超额确认 prompt）|
| `/api/report_record/withdraw` | POST | 调度员撤回报工记录（插入 history + 同步 5003）|
| `/api/report_record/history_full` | GET | 单条记录的完整审计历史 |

**修改操作事务结构**：
```python
# app.py L868-939
conn = storage._pool.connection()
try:
    cur = conn.cursor()
    cur.execute("SELECT * FROM process_sub_steps WHERE id=%s FOR UPDATE")  # 行级锁
    # START TRANSACTION + UPDATE + INSERT history + COMMIT
finally:
    conn.close()
```

### 5.3 质检记录管理（/api/quality_record/*）

> 直接操作 `container_center.quality_records` 表，通过 `RE-001` 事务包裹。

| 端点 | 方法 | 事务 |
|------|------|------|
| `/api/quality_record/list` | GET | 只读，无事务 |
| `/api/quality_record/update` | POST | RE-001: `UPDATE quality_records` + `INSERT data_regression_history` |
| `/api/quality_record/withdraw` | POST | RE-001: `UPDATE status='withdrawn'` + `INSERT data_regression_history` |
| `/api/quality_record/history_full` | GET | 只读，无事务 |

### 5.4 物料/外协/维修/排产记录管理

| 业务域 | 列表 | 修改 | 撤回 | 审计历史 |
|--------|------|------|------|---------|
| 物料 | `/api/material_record/list` | UPDATE + INSERT history | UPDATE status='withdrawn' | history_full |
| 外协 | `/api/outsource_record/list` | UPDATE | UPDATE is_deleted=1 | history_full |
| 维修 | `/api/repair_record/list` | UPDATE | UPDATE is_deleted=1 | — |
| 排产 | `/api/schedule_record/list` | UPDATE | UPDATE is_deleted=1 | history_full |

---

## 六、外部集成

### 6.1 与 5003 调度中心的集成

```
5008 (app.py)                              5003 (standalone_dispatch_server.py)
   │                                              │
   ├─ POST /api/dispatch-center/sync/sub-step-report
   │      (bridge.dispatch_center_sync.send_sub_step_report)
   │                                              │
   ├─ POST http://127.0.0.1:5003/api/dispatch-center/report-submitted
   │      (app.py L673) → 触发 WeChat 微信通知
   │                                              │
   ├─ bridge/dispatch_center_sync.send_quality_record()
   │      → 同步质检结果到 5003
   │                                              │
   └─ bridge/dispatch_center_sync.send_material_update()
          → 同步物料更新到 5003
```

### 6.2 容器中心 SSOT 代理

app.py L222-328 实现了两个代理端点：

| 端点 | 行为 |
|------|------|
| `GET /api/orders/full-status/<order_no>` | retry 2次 → fallback 到本地 `steel_belt.process_records` |
| `GET /api/orders/full-status-list` | retry 2次 → fallback 到本地 |

**fallback 场景**：容器中心（5002）不可用时，移动端仍可获取基本信息。

### 6.3 统一任务分流（/api/tasks）

app.py L1990-2029：`/api/tasks` 通过 UNION 查询 5 张独立表：

```sql
SELECT * FROM process_sub_steps UNION ALL
SELECT * FROM quality_records UNION ALL
SELECT * FROM material_records UNION ALL
SELECT * FROM outsource_records
ORDER BY created_at DESC LIMIT 100
```

---

## 七、安全架构

### 7.1 认证机制

| 机制 | 实现 | 位置 |
|------|------|------|
| Session | `session['logged_in']` + `session['user_id']` | 移动端登录 |
| JWT Token | `jwt.encode(payload, JWT_SECRET_KEY, HS256)` | app.py L141 |
| 操作员表 | `operators` 表，`is_active=1` 过滤 | app.py L124 |
| 降级机制 | JWT 失败 → base64 token | app.py L144 |

### 7.2 启动时校验

- **JWT_SECRET_KEY**：必须在 `.env` 中配置
- **前端 JS 语法检查**：`app.py L69-102` `_validate_frontend_js()`

---

## 八、关键 API 端点速查

### 8.1 报工核心

| 端点 | 方法 | 关键说明 |
|------|------|---------|
| `/api/process_sub_step` | POST | 报工提交，含幂等拦截、同步 5003、WeChat 通知 |
| `/api/process_sub_step/withdraw` | POST | 报工撤回，插入 history，同步 5003 |
| `/api/report_record/list` | GET | 报工记录列表 |
| `/api/report_record/update` | POST | 调度员修改（含超额确认 300 码）|
| `/api/report_record/withdraw` | POST | 调度员撤回报工 |

### 8.2 质检核心

| 端点 | 方法 | 关键说明 |
|------|------|---------|
| `/api/quality_record/list` | GET | 查 `container_center.quality_records` |
| `/api/quality_record/update` | POST | RE-001 事务，修改 + history |
| `/api/quality_record/withdraw` | POST | RE-001 事务，软删除 + history |

### 8.3 SSOT 代理

| 端点 | 方法 | 关键说明 |
|------|------|---------|
| `/api/orders/full-status/<order_no>` | GET | 代理容器中心，retry 2次 + fallback |
| `/api/orders/full-status-list` | GET | 同上，列表版本 |
| `/api/all-process-tasks` | GET | 工序任务汇总，含分页 |
| `/api/process-tasks/by-order/<order_no>` | GET | 按订单号查合并工序 |

### 8.4 调度管理

| 端点 | 方法 | 业务域 |
|------|------|-------|
| `/api/material_record/list` | GET | 物料 |
| `/api/material_record/update` | POST | 物料修改 |
| `/api/outsource_record/list` | GET | 外协 |
| `/api/repair_record/list` | GET | 维修 |
| `/api/schedule_record/list` | GET | 排产 |
| `/api/schedule/*` | * | 排产蓝图（schedule_bp）|
| `/api/dispatch-center/*` | * | 调度中心蓝图（dispatch_center_bp）|

---

## 九、已知架构特征

| 特征 | 说明 | 影响 |
|------|------|------|
| **单文件大入口** | `app.py` ≈ 2100 行，包含内联路由 | 路由分散，难以按功能模块快速定位 |
| **事务模式不统一** | 部分用 `START TRANSACTION`，部分用 `storage._pool.connection()` + 手动 commit | 代码一致性差 |
| **蓝图可选注册** | `stats/ai/cost/reports` 未实现时不报错 | 系统可降级运行，但缺少对应功能 |
| **双库访问** | `container_center` + `steel_belt` 同时存在 | 需注意数据一致性 |
| **同步桥接** | `bridge/dispatch_center_sync.py` 封装了对 5003 的 HTTP 调用 | 网络抖动时同步可能失败（已有 warning log）|

---

## 十、与 5010 库存系统的关系

| 对比项 | 5008 移动端报工 | 5010 库存管理 |
|--------|----------------|--------------|
| 入口文件 | `mobile_api_ai/app.py` | `inventory_api_server.py` |
| 端口 | 5008 | 5010 |
| 架构模式 | 单文件 + Blueprint 混合 | Blueprint 专用 |
| 数据库 | `container_center` + `steel_belt` | `inventory_db` + `steel_belt`（旧）|
| 事务控制 | 手动 `connection()` + `commit()` | 统一 `log_operation` + `_conn` 参数 |
| 审计日志 | 分散在各记录管理路由中 | 统一 `db_utils.log_operation()` |
| 健康检查 | `/health`（无 DB 检查）| `/api/health`（含 MySQL ping）|

> 5008 和 5010 是两个**独立服务**，通过 HTTP 调用（`inventory_external_bp`）或服务间通信（5008 → 5003 → 5010）交互。
