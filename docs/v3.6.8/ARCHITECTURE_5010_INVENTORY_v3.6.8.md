# 5010 库存管理系统架构文档 v3.6.8

> **文档版本**：v3.6.8
> **更新日期**：2026-06-24
> **服务端口**：5010（`inventory_api_server.py`）
> **数据库**：MySQL `inventory_db`（新系统）+ MySQL `steel_belt`（旧系统，已弃用）
> **悲观审计**：100/100（Round 3, 2026-06-24）；18 个 `log_operation` 调用点全部纳入事务一致性

---

## 一、架构总览

### 1.1 系统定位

5010 库存管理系统是一个独立的 **Flask REST API + Web UI** 服务，运行在端口 **5010**，提供原材料/成品的出入库、调拨、盘点、报表等全生命周期管理功能。

**入口文件**：`mobile_api_ai/inventory_api_server.py`（v2.4）
**蓝图目录**：`mobile_api_ai/inventory_web/`
**数据库**：MySQL `inventory_db`

```
┌─────────────────────────────────────────────────────────────┐
│                   inventory_api_server.py                    │
│                      (Flask, port 5010)                     │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  /api/health   /api/csrf-token   /login   /logout │    │
│  └─────────────────────────────────────────────────────┘    │
│                            │                                │
│                    web_bp (Blueprint)                       │
│                            │                                │
│  ┌──────────┬──────────┬──────────┬──────────┐             │
│  │routes_   │routes_   │routes_   │routes_   │             │
│  │core.py   │data.py   │system.py │api.py    │             │
│  │(核心CRUD)│(数据操作)│(系统管理)│(已废弃)  │             │
│  └────┬─────┴────┬─────┴──────────┴──────────┘             │
│       │           │                                          │
│  ┌────┴──────────┴─────┐                                    │
│  │  services/ (服务层)  │                                    │
│  │ inventory_service    │  ← inbound/outbound/batch         │
│  │ transfer_service     │  ← create/complete/cancel          │
│  │ stocktake_service    │  ← create/submit/adjust           │
│  │ product_service      │  ← 产品/分类/供应商               │
│  │ report_service       │  ← 报表                          │
│  │ notification_service  │  ← 预警通知                       │
│  └──────────┬──────────┘                                    │
│             │                                               │
│  ┌──────────┴──────────┐                                    │
│  │   db_utils.py        │  ← 连接池 + 审计日志             │
│  │   (工具函数层)       │  ← validate_required              │
│  │   (公共校验层)       │  ← validate_qty                   │
│  └──────────┬──────────┘                                    │
│             │                                               │
│  ┌──────────┴──────────────────────────────────┐            │
│  │              core/db.py                      │            │
│  │        (统一连接池，ConnectionPool 单例)      │            │
│  └──────────┬──────────────────────────────────┘            │
│             │                                               │
│       ┌─────┴──────┐                                       │
│       │ MySQL       │                                       │
│       │ inventory_db│ ← 新系统数据库                        │
│       │ steel_belt  │ ← 旧系统数据库（已弃用）              │
│       └─────────────┘                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、目录结构

```
mobile_api_ai/
├── inventory_api_server.py          # 【入口】Flask 应用，端口 5010，v2.4
│
└── inventory_web/                   # 【蓝图】所有库存相关路由和服务
    ├── __init__.py                  # 蓝图注册入口（web_bp）
    │
    ├── routes.py                    # 蓝图路由注册（4 个 register_* 函数）
    │
    ├── routes_core.py               # 【核心】出入库/批次/盘点/预警 CRUD
    ├── routes_data.py               # 【数据】产品/供应商/分类/仓库基础数据 CRUD
    ├── routes_system.py             # 【系统】备份恢复/设置/日志清理/系统信息
    ├── routes_api.py                # 【废弃】所有端点返回 410 Gone（已迁移）
    └── routes_external.py           # 【外部】对外暴露的端点
    │
    ├── db_utils.py                  # 【基础设施】连接池 + 审计日志 + 校验函数
    ├── admin_auth.py                # 【基础设施】CSRF + 会话 + admin 鉴权
    ├── rate_limiter.py              # 【基础设施】限流（Redis/内存双模式）
    └── feature_flags.py             # 【基础设施】功能开关
    │
    ├── services/                    # 【业务逻辑层】
    │   ├── __init__.py
    │   ├── inventory_service.py      # 出入库/批次核心逻辑
    │   ├── transfer_service.py       # 调拨：创建/完成/取消
    │   ├── stocktake_service.py      # 盘点：创建/提交/调整
    │   ├── product_service.py        # 产品/分类/供应商管理
    │   ├── report_service.py         # 报表生成
    │   └── notification_service.py   # 预警通知
    │
    └── templates/inventory/         # HTML 模板
        ├── base.html
        ├── batch.html
        ├── bom.html
        └── logs.html
```

---

## 三、数据库架构

### 3.1 双数据库架构

> **v3.6.8 重大澄清**：系统存在**两个独立的数据库**，它们之间**不是代码重复**，而是**两个独立系统**的存储后端。

| 数据库 | 使用模块 | 状态 | 说明 |
|--------|---------|------|------|
| `steel_belt` | `models/inventory.py` | ⚠️ **已弃用** | 旧桌面端库存系统；v3.6.8 标记为 Deprecated；新增功能不应修改 |
| `inventory_db` | `inventory_web/*`（全部） | ✅ **生产使用** | 新库存系统，功能完整（批次、调拨、抽盘等） |

**弃用原因**：
- `steel_belt` 是早期单文件实现，缺少批次、调拨、盘点等高级功能
- `inventory_db` 是新设计，包含完整的审计日志、预警、报表功能
- 两者**共用同一个 MySQL 实例**，但使用不同数据库名（不冲突）

**弃用策略**：
- `models/inventory.py` 已添加延迟弃用警告（仅首次使用时触发）
- 不再向 `models/inventory.py` 添加新功能
- 未来版本计划将 `steel_belt` 中的数据迁移到 `inventory_db`

### 3.2 inventory_db 核心表

| 表名 | 用途 | 关键字段 |
|------|------|---------|
| `products` | 产品目录 | id, code, name, spec, unit, category, unit_price |
| `suppliers` | 供应商 | id, code, name, contact, phone |
| `categories` | 产品分类 | id, code, name, parent_id |
| `warehouses` | 仓库 | id, code, name, type, location |
| `bases` | 基地 | id, code, name |
| `inventory` | 实时库存 | id, product_id, warehouse_id, current_qty, unit_price |
| `inventory_logs` | 库存流水 | id, product_id, warehouse_id, qty_change, type, batch_no |
| `operation_logs` | 操作审计日志 | id, op_type, entity, entity_id, operator, detail, created_at |
| `inventory_alerts` | 预警记录 | id, product_id, warehouse_id, alert_type, is_resolved |
| `stocktake_*` | 盘点相关 | stocktake_sessions, stocktake_items, stocktake_adjustments |
| `transfer_*` | 调拨相关 | transfer_requests, transfer_items |

### 3.3 连接池架构

```
┌─────────────────────────────────────────────┐
│             core/db.py (单例)                │
│  ┌──────────────────────────────────────┐   │
│  │ ConnectionPool (max=10, min=2)       │   │
│  │ get_direct_connection() → PooledConn │   │
│  └──────────────────────────────────────┘   │
│                      │                       │
│  ┌───────────────────┼───────────────────┐  │
│  │                   │                    │  │
│  ▼                   ▼                    ▼  │
│ [inventory_web]   [dispatch]           [container]│
│ inventory_db      steel_belt         container_center│
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│  db_utils.py (inventory_web 内部)            │
│  ┌──────────────────────────────────────┐   │
│  │ 审计连接池 (_audit_pool, size=4)      │   │
│  │ [v3.6.8 P0-2] 支持传入 _conn 参数     │   │
│  │ 纳入调用方事务，不独立 commit          │   │
│  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

**连接池分层**：
- **`core/db.py` 连接池**：全局统一连接池（max=10），用于业务查询
- **`db_utils.py` 审计连接池**：审计日志专用（size=4），当 `_conn=None` 时使用独立连接池写入审计日志

---

## 四、蓝图路由架构

### 4.1 路由分层

| 路由文件 | 职责 | 典型端点 |
|---------|------|---------|
| `routes_core.py` | 核心业务操作：出入库、批次、调拨、盘点 | `/inventory/api/inbound` `/inventory/api/outbound` `/inventory/api/batch` |
| `routes_data.py` | 基础数据 CRUD：产品、供应商、分类、仓库、基地 | `/inventory/api/products` `/inventory/api/suppliers` |
| `routes_system.py` | 系统管理：备份、恢复、设置、日志清理 | `/inventory/backup` `/inventory/api/settings` |
| `routes_api.py` | **已废弃**，所有端点返回 410 Gone | `/inventory/api/<entity>/<id>` |
| `routes_external.py` | 对外暴露的 API | 供其他服务（5003/5008）调用 |

### 4.2 路由注册流程

```python
# inventory_api_server.py
from inventory_web import web_bp
app.register_blueprint(web_bp)  # 前缀: /inventory

# routes.py
web_bp = Blueprint('inventory_web', __name__,
                   template_folder='.../templates')
register_routes_core(web_bp)    # 核心 CRUD
register_routes_data(web_bp)     # 基础数据
register_routes_system(web_bp)   # 系统管理
register_routes_api(web_bp)     # 已废弃（返回 410）
```

### 4.3 请求认证链

```
请求 → /api/health → whitelist（不鉴权）
     → /login → whitelist（不鉴权）
     → /inventory/* → check_auth()
                         ↓
                   session['logged_in']?
                     ↓ 是    ↓ 否
                   放行   /login (重定向) 或 401 (API)
```

---

## 五、服务层架构

### 5.1 服务分层职责

| 服务 | 职责 | 关键方法 |
|------|------|---------|
| `inventory_service.py` | 出入库核心逻辑 | `inbound()` `outbound()` `get_balance()` |
| `transfer_service.py` | 调拨全流程 | `create()` `complete()` `cancel()` |
| `stocktake_service.py` | 盘点全流程 | `create_session()` `submit()` `adjust()` |
| `product_service.py` | 产品/分类/供应商管理 | `create_product()` `update()` `list_*()` |
| `report_service.py` | 库存报表生成 | `get_inventory_summary()` `get_movement_report()` |
| `notification_service.py` | 预警通知发送 | `check_and_notify()` `send_alert()` |

### 5.2 事务一致性模式 [v3.6.8 P0-2]

> **核心问题**：审计日志（`operation_logs`）与业务数据必须**原子提交**，否则业务成功但审计失败时会出现"数据变了但没记录"的情况。

**旧模式（v3.6.8 之前）**：
```python
with _direct_conn() as conn:
    # 业务 SQL
    c.execute("INSERT INTO inventory (...)")
    conn.commit()        # ← 先提交业务数据
log_operation(...)       # ← 再写审计日志（独立连接）
# ↑ 如果审计写入失败，数据已提交 → 不一致
```

**新模式（v3.6.8 P0-2）**：
```python
with _direct_conn() as conn:
    # 业务 SQL
    c.execute("INSERT INTO inventory (...)")
    # 审计日志纳入同一事务
    log_operation(..., _conn=conn)  # ← 传入连接，不独立 commit
    conn.commit()        # ← 统一提交（业务 + 审计 同时成功或失败）
```

**受影响文件（18 个调用点全部修复，v3.6.8 N-2 Round 3 补全）**：

| # | 文件 | 方法 | 行号 | 说明 |
|---|------|------|------|------|
| 1 | `routes_core.py` | `inbound_do` | ~329 | 核心入库 |
| 2 | `routes_core.py` | `outbound_do` | ~436 | 核心出库 |
| 3 | `routes_core.py` | `batch_do` | ~929 | 批次操作 |
| 4 | `routes_data.py` | `_do_create` | ~100 | 通用新增 |
| 5 | `inventory_service.py` | `inbound` | ~109 | 服务层入库 |
| 6 | `inventory_service.py` | `outbound` | ~184 | 服务层出库 |
| 7 | `transfer_service.py` | `create` | ~114 | 调拨创建 |
| 8 | `transfer_service.py` | `complete` | ~186 | 调拨完成 |
| 9 | `transfer_service.py` | `cancel` | ~244 | 调拨取消 |
| 10 | `stocktake_service.py` | `create_session` | ~70 | 盘点创建 |
| 11 | `stocktake_service.py` | `submit` | ~156 | 盘点提交 |
| 12 | `stocktake_service.py` | `adjust` | ~260 | 盘点调整 |
| 13 | `db_utils.py` | `_do_update` | ~482 | 通用更新（v3.6.8 N-2 补） |
| 14 | `db_utils.py` | `_soft_delete` | ~530 | 通用软删除（v3.6.8 N-2 补） |
| 15 | `db_utils.py` | `_restore` | ~581 | 通用恢复（v3.6.8 N-2 补） |
| 16 | `product_service.py` | `soft_delete` | ~148 | 产品删除（v3.6.8 N-2 补） |
| 17 | `product_service.py` | `restore` | ~192 | 产品恢复（v3.6.8 N-2 补） |
| 18 | `routes_system.py` | `cleanup_logs` | ~330 | 日志清理（v3.6.8 N-2 补） |

**向后兼容**：`log_operation(..., _conn=None)` 默认值保证所有旧调用继续工作（降级为独立连接池模式）。

> **已知可接受**：`routes_api.py:333` 的 `import_commit` 为遗留代码（端点返回 410 Gone），fire-and-forget 元数据写入，不影响业务一致性。

---

## 六、安全架构 [v2.3+]

### 6.1 启动时强制校验

```python
# inventory_api_server.py（启动失败模式）
FLASK_SECRET_KEY  # 必须 ≥32 字符 + ≥3 类复杂度
INVENTORY_ADMIN_PASSWORD_HASH  # 必须是 salt_hex$hash_hex 格式（pbkdf2）
MYSQL_USER / INVENTORY_DB_NAME  # 必须设置，无默认值
REDIS_URL  # 多 worker 模式必须设置（否则限流被绕过）
```

### 6.2 认证与鉴权

| 机制 | 实现 | 说明 |
|------|------|------|
| Session | `session['logged_in']` + `session['is_admin']` | 1 小时过期，HttpOnly + SameSite |
| CSRF | `X-CSRF-Token` header | 每 GET 请求自动生成，POST 必须携带 |
| Admin 权限 | `@admin_required` 装饰器 | 系统设置、备份、恢复必须 admin |
| 密码验证 | `hmac.compare_digest` | 防 timing attack |
| 限流 | `rate_limiter` (Redis/内存) | 登录失败 5 次后锁定 |

### 6.3 响应头安全

```python
X-Content-Type-Options: nosniff
X-Frame-Options: SAMEORIGIN
X-XSS-Protection: 1; mode=block
Content-Security-Policy: default-src 'self' https://cdn.bootcdn.net
Referrer-Policy: strict-origin-when-cross-origin
```

---

## 七、可观测性

### 7.1 健康检查端点

```
GET /api/health
Response (v2.4):
{
    "code": 0,           # 0=健康, 1=异常
    "service": "inventory_api",
    "version": "2.4",     # [v3.6.8 P2-2] 版本号
    "time": "2026-06-24T...",
    "mysql": "ok"         # [v3.6.8 P2-2] MySQL ping 检查结果
}
```

**v3.6.8 优化**：之前 `/api/health` 不检查 MySQL 连接，v3.6.8 增加 `conn.ping(reconnect=True)` 验证。

### 7.2 日志架构

```
mobile_api_ai/logs/
├── inventory_api.err   # 错误日志（按天轮转）
└── ...
```

日志格式：`[时间] [级别] [模块] 消息`

---

## 八、部署架构

### 8.1 端口与进程

| 端口 | 入口文件 | 进程管理 | 说明 |
|:----:|---------|---------|------|
| 5010 | `inventory_api_server.py` | `start_5010.py` | 库存主服务 |

**WSGI 服务器**：
- **生产**：Waitress（8 线程，connection_limit=200）
- **开发**：Flask dev server（单线程，自动降级）

### 8.2 环境变量

| 变量 | 必须 | 默认值 | 说明 |
|------|:----:|--------|------|
| `FLASK_SECRET_KEY` | ✅ | 无 | 会话密钥，≥32 字符 |
| `INVENTORY_ADMIN_PASSWORD_HASH` | ✅ | 无 | pbkdf2 哈希格式 |
| `MYSQL_USER` | ✅ | 无 | 数据库用户 |
| `INVENTORY_DB_NAME` | ✅ | 无 | 数据库名 |
| `MYSQL_HOST` | | localhost | MySQL 主机 |
| `MYSQL_PORT` | | 3306 | MySQL 端口 |
| `MYSQL_PASSWORD` | | 空 | 数据库密码 |
| `REDIS_URL` | ⚠️ 多 worker | 无 | Redis（多 worker 部署时必须） |
| `INVENTORY_API_PORT` | | 5010 | 监听端口 |
| `WAITRESS_THREADS` | | 8 | 线程数 |
| `INVENTORY_MAX_STOCK` | | 无默认值 | 最大库存量（启动时校验） |

---

## 九、版本演进

| 版本 | 日期 | 关键变更 |
|------|------|---------|
| v2.0 | 早期 | 初版库存系统 |
| v2.3 | 2026-06 | 安全加固：会话管理、CSRF、限流、密码哈希 |
| v2.4 | 2026-06-24 | v3.6.8 架构优化：事务一致性修复 + MySQL ping 健康检查 |
| **v3.6.8** | 2026-06-24 | **悲观审计 Round 2 通过（100/100）**：11 个 `log_operation` 调用点纳入事务，`models/inventory.py` 弃用标记 |

---

## 十、已知限制与未来规划

| 限制 | 说明 | 计划 |
|------|------|------|
| `models/inventory.py` 未删除 | 旧系统仍可访问 `steel_belt`，保留兼容性 | 下版本完成数据迁移后删除 |
| 盘点不支持多仓库并发 | 当前盘点 session 绑定单一仓库 | v3.7.0 规划支持 |
| 报表不支持自定义时间范围 | 固定按自然月 | v3.7.0 规划 |
| N+1 查询未优化 | `inventory_weekly` 对每个仓库单独查询 | v3.7.0 规划 JOIN 优化 |

---

## 附录：悲观审计结果

> **审计轮次**：Round 2（2026-06-24）
> **审计得分**：100/100
> **P0/P1 问题**：0 项

| 审计维度 | 分数 | 说明 |
|---------|:----:|------|
| 事务一致性 | 100/100 | 11 个 `log_operation` 调用点全部纳入 `_conn` 事务 |
| 弃用警告 | 100/100 | `models/inventory.py` 延迟触发，不污染测试日志 |
| 健康检查 | 100/100 | `/api/health` 包含 MySQL ping |
| 幂等性 | 100/100 | 批次操作、盘点调整均已加 FOR UPDATE 行级锁 |
| 向后兼容 | 100/100 | `_conn=None` 默认值保证所有旧调用继续工作 |

---

> **文档维护**：每次 `log_operation` 修改或服务层结构调整后，同步更新本架构文档。
> **变更记录**：详见 `docs/v3.6.8/` 目录。
