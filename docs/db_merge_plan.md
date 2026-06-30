# 双连接管理器合并方案 — 阶段0止血

> 产出时间: 2026-06-07 | 基于 code-level 深读

---

## 0. 现状诊断摘要

### 比审计报告更糟的发现

深读源码后发现：**不只是"两套并存"，而是同一套类被复制了两份**。

| 类/函数 | 文件A | 文件B | 文件C |
|---------|-------|-------|-------|
| `MySQLConnectionPool` | `connection_pool.py:L18` | `_database_legacy.py:L71` | — |
| `PooledConnection` | `connection_pool.py:L100` | `_database_legacy.py:L154` | — |
| `_get_db_config()` | `config.py:L5` | `_database_legacy.py:L38` | `core/database.py:L44` |
| `MYSQL_CONFIG` | `config.py:L17` | `_database_legacy.py:L51` | — |
| `reload_db_config()` | `connection_pool.py:L172` | `_database_legacy.py:L54` | — |
| `get_connection()` | `connection_pool.py:L159` | `_database_legacy.py` L约200 | — |

**实际有 3 个连接入口，其中 2 个是同一套代码的复制品。**

### SQLite 双模式真实状态

`core/database.py::DatabaseManager` 是**唯一**支持 SQLite 的地方（已被 6 个文件引用但实际业务路径是否触发存疑）。项目 MEMORY.md 写"steel_belt 只读"，实际上 SQLite 模式仅用于本地开发/离线场景，生产环境只走 MySQL。

**结论: SQLite 模式应保留但降级为"开发/测试模式"，不参与生产路径。**

### 80+ 文件引用 `models.database` 的真实路径

```
models.database.__init__ →
  ├── from ._database_legacy import *     → 72KB 遗留类 (含重复的 MySQLConnectionPool)
  ├── from .config import _get_db_config, MYSQL_CONFIG
  ├── from .connection_pool import MySQLConnectionPool, PooledConnection, get_connection, get_connection_context, reload_db_config
  └── from .utils_db import ...
```

`base_dao.py:L17` 只取 `from models.database import get_connection` → 走的是 `connection_pool.py::get_connection()`。

**但 `_database_legacy.py` 中还有大量函数被 `import *` 导出，desktop/views 和 services 可能调用了遗留代码中的连接函数。**

---

## 1. 统一设计

### 1.1 统一连接管理器: `DB`

```python
# 新文件: core/db.py  (或 models/database/db.py)
# 文件名 db.py 短小，避免与 database.py 混淆

class DB:
    """统一数据库连接管理器"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls): ...
    def init(self, config: dict = None): ...
    def get_connection(self) -> PooledConnection: ...
    def get_cursor(self, commit=True) -> ContextManager: ...
    def execute(self, sql, params=None) -> List[Dict]: ...
    def execute_update(self, sql, params=None) -> int: ...
    def execute_insert(self, sql, params=None) -> int: ...
    def close_all(self): ...
```

### 1.2 API 统一

| 旧调用 | 新调用 | 说明 |
|--------|--------|------|
| `get_connection()` | `DB().get_connection()` 或 `db.get_connection()` | 返回 PooledConnection |
| `with get_connection_context() as conn:` | `with DB().cursor() as cur:` | 简化上下文 |
| `db.get_cursor()` (DatabaseManager) | `DB().cursor()` | 统一命名 |
| `conn.close()` (PooledConnection) | → 自动归还池 | 保持不变 |

### 1.3 连接池策略

- **统一池化**: 永远走连接池，不再"即用即抛"
- **池大小**: 默认 10，环境变量 `DB_POOL_SIZE` 覆盖，范围 [5, 50]
- **空闲超时**: 默认 300s，环境变量 `DB_POOL_IDLE_TIMEOUT`
- **最大生命周期**: 默认 3600s，到期自动回收重建
- **连接验证**: 每次从池取出时 `conn.ping(reconnect=True)`
- **SQLite 模式**: 保留但仅当 `USE_SQLITE=true` 时启用，生产不触发

### 1.4 配置统一

```python
# 单一配置文件: models/database/config.py (扩展到支持所有场景)

def get_db_config():
    """统一数据库配置 — 所有代码唯一入口"""
    if os.getenv('USE_SQLITE', '').lower() == 'true':
        return _get_sqlite_config()
    return _get_mysql_config()

def _get_mysql_config():
    return {
        "host": os.getenv('DB_HOST', os.getenv('MYSQL_HOST', 'localhost')),
        "port": int(os.getenv('DB_PORT', os.getenv('MYSQL_PORT', '3306'))),
        "user": os.getenv('DB_USER', os.getenv('MYSQL_USER', 'root')),
        "password": os.getenv('DB_PASSWORD', os.getenv('MYSQL_PASSWORD', '')),
        "database": os.getenv('DB_NAME', os.getenv('MYSQL_DATABASE', 'steel_belt')),
        "charset": "utf8mb4",
        "pool_size": int(os.getenv('DB_POOL_SIZE', '10')),
        "connect_timeout": int(os.getenv('DB_CONNECT_TIMEOUT', '10')),
    }
```

**向后兼容**: `MYSQL_*` 环境变量继续有效（作为 fallback），推荐新项目使用 `DB_*` 前缀。

### 1.5 事务支持

```python
# DB.transaction() — 统一事务上下文
with DB().transaction() as conn:
    conn.cursor().execute("INSERT ...")
    conn.cursor().execute("UPDATE ...")
    # 自动 commit，异常自动 rollback
```

### 1.6 全局实例

```python
# core/db.py 底部
db = DB()  # 全局单例，可直接 import
```

---

## 2. 迁移步骤

### Step 1: 创建统一管理器（风险: LOW）

**操作:**
1. 创建 `core/db.py`，包含 `DB` 类 + `PooledConnection` + `get_connection()` 兼容包装
2. 初始化逻辑：自动从环境变量读配置 + `init()`
3. 单元测试：`tests/unit/core/test_db.py`（覆盖连接池、cursor、事务、配置回退）
4. 验证：`pytest tests/unit/core/test_db.py -v`

**不删除任何旧文件，纯增量。**

### Step 2: 重定向 `models.database.__init__`（风险: MEDIUM）

**操作:**
1. 修改 `models/database/__init__.py`，改为从 `core.db` 导入：
   ```python
   # 新版 __init__.py
   from core.db import DB, db, get_connection, get_connection_context
   from .config import get_db_config, MYSQL_CONFIG, _get_db_config
   from .connection_pool import (
       MySQLConnectionPool, PooledConnection,
       reload_db_config,
   )
   from .utils_db import (...)
   # ⚠️ 不再 from ._database_legacy import * — 改为显式导入需要的函数
   ```
2. 检查 `_database_legacy.py` 中实际被外部调用的函数名（运行测试看报错）
3. 将必需的遗留函数显式导入
4. 运行全量测试：`pytest -x --tb=short`
5. 修复所有 import 报错

### Step 3: 移除 `core/database.py::DatabaseManager`（风险: MEDIUM）

**操作:**
1. 找到所有 `from core.database import ...` / `from core import database` 的引用（6 个文件）
2. 逐个改为 `from core.db import db` 或 `from models.database import get_connection`
3. 更新 `tests/unit/core/test_database.py` → 改为测试新的 `core/db.py`
4. 删除 `core/database.py`（或重命名为 `_database_old.py` 保留一个版本做保险）
5. 验证：全量测试

### Step 4: 替换生产路径中的裸 `pymysql.connect()`（风险: HIGH）

**范围**: 排除 `scripts/`、`scripts/archive/`、`mobile_api_ai/scripts/`、`打包脚本/`、`dist/`、根目录 `_*.py` 临时脚本

**核心需要改的生产文件（按优先级）:**

| 优先级 | 文件 | 行数 | 操作 |
|--------|------|------|------|
| P0 | `backup_system.py:L23` | 1处 | 改 `pymysql.connect(**MYSQL_CONFIG)` → `db.get_connection()` |
| P0 | `desktop/views/db_settings_window.py:L120` | 1处 | 改连接测试 → 使用 DB().get_connection() |
| P0 | `desktop/views/order_query_view.py:L416` | 1处 | 同上 |
| P0 | `desktop/views/settings_dialog.py:L430` | 1处 | 同上 |
| P0 | `services/inventory_sync.py:L45` | 1处 | 改 → db.get_connection() |
| P0 | `health_checker_integration.py:L79` | 1处 | 同上 |
| P1 | `mobile_api_ai/app.py:L199,432,470` | 3处 | 改 → db.get_connection() |
| P1 | `mobile_api_ai/dispatch_center/_core.py:L1543,1576,1601,1620,2892` | 5处 | 同上 |
| P1 | `mobile_api_ai/models/database.py:L35,48` | 2处 | 全部删除此文件，改为 import db |
| P1 | `mobile_api_ai/container_center_v5.py:L1342` | 1处 | 改 |
| P1 | `mobile_api_ai/container_center_api.py:L2555` | 1处 | 改 |
| P1 | `mobile_api_ai/config_center.py:L260` | 1处 | 改 |
| P1 | `mobile_api_ai/sync_bridge.py:L148` | 1处 | 改 |
| P1 | `mobile_api_ai/sync/__init__.py:L29` | 1处 | 改 |
| P1 | `mobile_api_ai/sync/sync_log.py:L21` | 1处 | 改 |
| P1 | `mobile_api_ai/wechat_message_store.py:L37,43` | 2处 | 改 |
| P1 | `mobile_api_ai/operation_log.py:L31` | 1处 | 改 |
| P1 | `mobile_api_ai/api/quality.py:L18` | 1处 | 改 |
| P1 | `mobile_api_ai/api/process.py:L20` | 1处 | 改 |
| P1 | `mobile_api_ai/api/process_v2.py:L137` | 1处 | 改 |
| P1 | `mobile_api_ai/face_checkin/__init__.py:L150` | 1处 | 改 |
| P1 | `mobile_api_ai/services/stats_engine.py:L241,255` | 2处 | 改 |
| P1 | `mobile_api_ai/services/cost_service.py:L203,253` | 2处 | 改 |
| P1 | `mobile_api_ai/container_center/storage/mysql_router.py:L19` | 1处 | 改 |
| P1 | `mobile_api_ai/inventory_api_server.py:L172,177` | 2处 | 改 |
| P1 | `mobile_api_ai/inventory_web/db_utils.py:L218,286,311,336` | 4处 | 改 |
| P1 | `utils/db_utils.py:L68,114` | 2处 | 改 |
| P1 | `utils/auto_schema.py:L140` | 1处 | 改 |
| P1 | `mobile_api_ai/storage/mysql_storage.py` | 1处 | 改 |

### Step 5: 清理 `_database_legacy.py` 中的重复类（风险: MEDIUM）

**操作:**
1. 从 `_database_legacy.py` 中删除重复的 `MySQLConnectionPool` + `PooledConnection` + `_get_db_config` + `MYSQL_CONFIG` + `reload_db_config`（L31-L170）
2. 改为 `from core.db import DB, db` + `from .config import ...`
3. 验证 `_database_legacy.py` 中剩余函数是否正常
4. 全量测试

### Step 6: 最终清理（风险: LOW）

1. 删除 `core/database.py`（已无引用）
2. 删除 `models/database/connection_pool.py`（逻辑已搬到 `core/db.py`）
3. 清理 `models/database/config.py` → 合并到 `core/db.py` 或保留为配置模块
4. 更新 `MEMORY.md` 中的存储层规则
5. 全量回归测试

---

## 3. 文件改动清单

| 文件 | 操作 | 风险 |
|------|------|------|
| `core/db.py` | **新增** | — |
| `tests/unit/core/test_db.py` | **新增** | — |
| `models/database/__init__.py` | 修改 | MEDIUM |
| `models/database/_database_legacy.py` | 修改（删除重复类 L31-L170） | MEDIUM |
| `core/database.py` | 删除（Step 6） | LOW |
| `models/database/connection_pool.py` | 删除（Step 6） | LOW |
| `backup_system.py` | 1行替换 | LOW |
| `desktop/views/db_settings_window.py` | 1处替换 | LOW |
| `desktop/views/order_query_view.py` | 1处替换 | LOW |
| `desktop/views/settings_dialog.py` | 1处替换 | LOW |
| `services/inventory_sync.py` | 1处替换 | LOW |
| `health_checker_integration.py` | 1处替换 | LOW |
| `mobile_api_ai/app.py` | 3处替换 | MEDIUM |
| `mobile_api_ai/dispatch_center/_core.py` | 5处替换 | HIGH |
| `mobile_api_ai/models/database.py` | 全文件重构 | MEDIUM |
| `mobile_api_ai/container_center_v5.py` | 1处替换 | MEDIUM |
| `mobile_api_ai/container_center_api.py` | 1处替换 | MEDIUM |
| `mobile_api_ai/config_center.py` | 1处替换 | MEDIUM |
| `mobile_api_ai/sync_bridge.py` | 1处替换 | MEDIUM |
| `mobile_api_ai/sync/__init__.py` | 1处替换 | MEDIUM |
| `mobile_api_ai/sync/sync_log.py` | 1处替换 | LOW |
| `mobile_api_ai/wechat_message_store.py` | 2处替换 | MEDIUM |
| `mobile_api_ai/operation_log.py` | 1处替换 | LOW |
| `mobile_api_ai/api/quality.py` | 1处替换 | LOW |
| `mobile_api_ai/api/process.py` | 1处替换 | LOW |
| `mobile_api_ai/api/process_v2.py` | 1处替换 | LOW |
| `mobile_api_ai/face_checkin/__init__.py` | 1处替换 | LOW |
| `mobile_api_ai/services/stats_engine.py` | 2处替换 | MEDIUM |
| `mobile_api_ai/services/cost_service.py` | 2处替换 | MEDIUM |
| `mobile_api_ai/container_center/storage/mysql_router.py` | 1处替换 | MEDIUM |
| `mobile_api_ai/inventory_api_server.py` | 2处替换 | MEDIUM |
| `mobile_api_ai/inventory_web/db_utils.py` | 4处替换 | MEDIUM |
| `mobile_api_ai/storage/mysql_storage.py` | 1处替换 | MEDIUM |
| `utils/db_utils.py` | 2处替换 | MEDIUM |
| `utils/auto_schema.py` | 1处替换 | MEDIUM |
| 相关测试文件 | 适配修改 | MEDIUM |

**总计: 新增 2 文件, 修改 ~30 文件, 删除 2 文件**

---

## 4. 回滚方案

- **Step 1-2 可独立回滚**: 删除 `core/db.py`，恢复旧 `__init__.py`
- **每个 Step 独立 commit**: git 可精确回滚到任意一步
- **旧文件保留**: `core/database.py` 重命名为 `_database_old.py` 而非直接删除
- **环境变量开关**: 如出问题，设置 `USE_LEGACY_DB=true` → 跳过新管理器走旧逻辑（实现成本低）

---

## 5. 72KB 遗留代码处理策略

**短期（本次止血）**: 
- 删除其中的重复类（L31-L170，约 140 行）
- `import *` 改为显式导入（只导出实际被外部使用的函数）
- 标记为 `@deprecated`，加注释指向新 API

**中期（后续清理）**:
- 将 `_database_legacy.py` 中剩余的有效函数拆分为子模块
- 淘汰过期函数

---

## 6. 待确认问题

| # | 问题 | 建议 |
|---|------|------|
| 1 | SQLite 模式是否仍在用？有生产场景吗？ | 保留但仅开发模式启用 |
| 2 | `CONTAINER_MYSQL_CFG` 连接的是独立 MySQL 还是同一个？ | 如是独立库，需要单独的 DB 实例 |
| 3 | 是否允许在 `core/db.py` 中统一所有数据库连接（包括 container_center）？ | 建议统一，但 container_center 可能连不同库 |
| 4 | 测试中大量 mock pymysql.connect，改后测试也要大改？ | 是，预计 ~20 个测试文件需要适配 |
| 5 | 是否暂时跳过 `_database_legacy.py` 的清理，先把连接管理器统一？ | 建议 Step 5 放到第二优先级 |
