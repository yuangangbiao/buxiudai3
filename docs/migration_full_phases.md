# MySQL 直写迁移 — 全面分阶段实施方案

**基准**: system_design.md v6.1 (737行)  
**总计**: 46 文件, 5 阶段, 逐行逐文件全覆盖

---

## 阶段零: 前置准备 (1 文件, 0 代码改动)

### P0.1 — MySQL 确认

```sql
-- 确认两个库存在
SHOW DATABASES LIKE 'steel_belt';
SHOW DATABASES LIKE 'container_center';

-- 确认 container_center 中所有业务表存在
USE container_center;
SHOW TABLES;
-- 预期: data_packages, sync_logs, dispatch_commands, data_flow_logs,
--        data_collection_records, workers, attendance, operation_logs,
--        enterprise_structure, product_flow_map, sub_step_audit_log,
--        schedule_records, return_records, sync_retry_queue
```

### P0.2 — .env 确认

```env
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=88888888          # ← 必须配置
MYSQL_DATABASE=steel_belt
CONTAINER_MYSQL_DATABASE=container_center  # ← 新增
```

---

## 阶段一: T01 配置层 (5 文件)

### 文件 1: `core/config.py`

| 操作 | 内容 |
|------|------|
| **新增** | `CONTAINER_MYSQL_CFG` 字典 |
| **新增** | `DB_CONNECT_TIMEOUT` 常量 |
| **删除** | `DB_PATHS['wechat_container']` |
| **删除** | `DB_PATHS['container_center']` |
| **删除** | `DB_PATHS['scheduler_configs']` 路径中的 SQLite 引用 |

```python
# ========== 在 core/config.py 中新增以下内容 ==========

# 位置: 在 MYSQL_CFG 定义之后 (~L220)

import os

DB_CONNECT_TIMEOUT = int(os.getenv('DB_CONNECT_TIMEOUT', '5'))

CONTAINER_MYSQL_CFG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', ''),
    'database': os.getenv('CONTAINER_MYSQL_DATABASE', 'container_center'),
    'charset': 'utf8mb4',
}

# ========== 注释以下 DB_PATHS 条目 ==========
# 'wechat_container': ...,     # 已迁移至 MySQL container_center
# 'container_center': ...,     # 已迁移至 MySQL container_center
```

### 文件 2: `.env`

```
# 新增行:
CONTAINER_MYSQL_DATABASE=container_center
DB_CONNECT_TIMEOUT=5

# 确认存在:
MYSQL_PASSWORD=88888888
```

### 文件 3: `.env.example`

```
# 同步 .env 新增:
CONTAINER_MYSQL_DATABASE=container_center
DB_CONNECT_TIMEOUT=5
```

### 文件 4: `mobile_api_ai/storage_mysql.py`

#### 4.1 — 修改 MYSQL_CFG 导入

```python
# 删除 L26-33 (本地 MYSQL_CFG 定义)
#    MYSQL_CFG = {
#        'host': os.environ.get('MYSQL_HOST', '127.0.0.1'),
#        ...
#        'database': os.environ.get('CONTAINER_MYSQL_DATABASE', 'container_center'),
#    }

# 改为:
from core.config import CONTAINER_MYSQL_CFG as MYSQL_CFG, DB_CONNECT_TIMEOUT
```

#### 4.2 — 补充 container_center 缺失的 12 个表 DDL

```python
# 在 TABLES_DDL 字典中新增以下表:

TABLES_DDL = {
    # === 原有表 (保持不变) ===
    'data_packages': """...""",
    'sync_logs': """...""",
    # ...

    # === 新增 container_center 表 ===
    'dispatch_commands': """
        CREATE TABLE IF NOT EXISTS dispatch_commands (
            id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            command_type VARCHAR(64) NOT NULL DEFAULT '',
            target_id VARCHAR(128) NOT NULL DEFAULT '',
            params JSON,
            status VARCHAR(32) NOT NULL DEFAULT 'pending',
            priority INT NOT NULL DEFAULT 0,
            process_name VARCHAR(128) DEFAULT '',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_status (status),
            INDEX idx_target (target_id),
            INDEX idx_process_name (process_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    'data_flow_logs': """
        CREATE TABLE IF NOT EXISTS data_flow_logs (
            id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            event_type VARCHAR(64) NOT NULL DEFAULT '',
            flow_type VARCHAR(64) DEFAULT '',
            source VARCHAR(128) DEFAULT '',
            target VARCHAR(128) DEFAULT '',
            status VARCHAR(32) DEFAULT '',
            detail JSON,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_event_type (event_type),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    'data_collection_records': """
        CREATE TABLE IF NOT EXISTS data_collection_records (
            id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            record_type VARCHAR(64) NOT NULL DEFAULT '',
            data_type VARCHAR(64) DEFAULT '',
            source_id VARCHAR(128) DEFAULT '',
            collected_at DATETIME,
            data JSON,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_data_type (data_type),
            INDEX idx_record_type (record_type)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    'workers': """
        CREATE TABLE IF NOT EXISTS workers (
            id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            enterprise_id VARCHAR(64) NOT NULL DEFAULT '',
            name VARCHAR(128) NOT NULL DEFAULT '',
            phone VARCHAR(32) DEFAULT '',
            role VARCHAR(64) DEFAULT '',
            department VARCHAR(128) DEFAULT '',
            status VARCHAR(32) DEFAULT 'active',
            sync_at DATETIME,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_enterprise_id (enterprise_id),
            INDEX idx_name (name),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    'attendance': """
        CREATE TABLE IF NOT EXISTS attendance (
            id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            worker_id VARCHAR(64) NOT NULL DEFAULT '',
            date DATE NOT NULL,
            check_in DATETIME,
            check_out DATETIME,
            status VARCHAR(32) DEFAULT 'pending',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_worker_date (worker_id, date),
            INDEX idx_date (date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    'operation_logs': """
        CREATE TABLE IF NOT EXISTS operation_logs (
            id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            operation_type VARCHAR(64) NOT NULL DEFAULT '',
            operator_id VARCHAR(64) DEFAULT '',
            target_type VARCHAR(64) DEFAULT '',
            target_id VARCHAR(128) DEFAULT '',
            detail JSON,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_operator (operator_id),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    'enterprise_structure': """
        CREATE TABLE IF NOT EXISTS enterprise_structure (
            id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            departments JSON,
            users JSON,
            operators JSON,
            updated_at DATETIME,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    'product_flow_map': """
        CREATE TABLE IF NOT EXISTS product_flow_map (
            id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            product_type_id VARCHAR(64) NOT NULL DEFAULT '',
            flow_type VARCHAR(64) NOT NULL DEFAULT '',
            process_name VARCHAR(128) DEFAULT '',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_product_flow (product_type_id, flow_type),
            INDEX idx_flow_type (flow_type)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    'sub_step_audit_log': """
        CREATE TABLE IF NOT EXISTS sub_step_audit_log (
            id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            sub_step_id VARCHAR(64) NOT NULL DEFAULT '',
            order_no VARCHAR(64) DEFAULT '',
            process_code VARCHAR(64) DEFAULT '',
            step_name VARCHAR(128) DEFAULT '',
            quantity DECIMAL(10,2) DEFAULT 0,
            operator VARCHAR(64) DEFAULT '',
            action VARCHAR(32) DEFAULT '',
            action_by VARCHAR(64) DEFAULT '',
            reason TEXT,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_order_no (order_no),
            INDEX idx_sub_step_id (sub_step_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    'schedule_records': """
        CREATE TABLE IF NOT EXISTS schedule_records (
            id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            order_id VARCHAR(64) NOT NULL DEFAULT '',
            scheduled_date DATE,
            machine_id VARCHAR(64) DEFAULT '',
            status VARCHAR(32) DEFAULT 'pending',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_order_id (order_id),
            INDEX idx_scheduled_date (scheduled_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    'return_records': """
        CREATE TABLE IF NOT EXISTS return_records (
            id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            order_id VARCHAR(64) NOT NULL DEFAULT '',
            reason TEXT,
            returned_qty DECIMAL(10,2) DEFAULT 0,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_order_id (order_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,

    'sync_retry_queue': """
        CREATE TABLE IF NOT EXISTS sync_retry_queue (
            id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            event_type VARCHAR(64) NOT NULL DEFAULT '',
            payload JSON,
            retry_count INT NOT NULL DEFAULT 0,
            next_retry_at DATETIME,
            status VARCHAR(32) DEFAULT 'pending',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_status_next (status, next_retry_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
}
```

#### 4.3 — 新增微信消息动态建表函数

```python
# 在文件末尾新增:

def _ensure_wechat_message_table(conn):
    """确保当前月份的微信消息表存在"""
    from datetime import datetime
    now = datetime.now()
    table_name = f'wechat_messages_{now.year}_{now.month:02d}'
    cur = conn.cursor()
    cur.execute(f'''CREATE TABLE IF NOT EXISTS `{table_name}` (
        id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        msg_id VARCHAR(64),
        from_user VARCHAR(64),
        to_user VARCHAR(64),
        msg_type VARCHAR(32),
        content TEXT,
        raw_xml TEXT,
        response TEXT,
        status VARCHAR(32) DEFAULT 'received',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_msg_id (msg_id),
        INDEX idx_from_user (from_user),
        INDEX idx_created_at (created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
    cur.close()
```

### 文件 5: `mobile_api_ai/mysql_storage.py`

```python
# 删除本地 MYSQL_CFG 定义 (~L50-L58)
# 改为:
from core.config import MYSQL_CFG, DB_CONNECT_TIMEOUT
```

---

## 阶段二: T02 Router 废弃 (12 文件)

### 文件 6: `container_center/storage/router.py`

```python
# 🗑️ 整个文件删除
```

### 文件 7: `container_center/storage/__init__.py`

```python
# 删除:
# from .router import DatabaseRouter

# 改为:
# # DatabaseRouter 已废弃，统一使用 storage_mysql.MySQLStorage
```

### 文件 8: `container_center/storage/document_store.py`

```python
# 删除 L7:
# from .router import DatabaseRouter

# 构造函数改造:
# 原: def __init__(self, router: DatabaseRouter):
# 改: def __init__(self, config: dict):
#        self._cfg = config
#        self._conn = None

# _get_conn() 改造:
# 原: 通过 self.router.get_db_cursor_by_name(db_name)
# 改:
def _get_conn(self):
    if self._conn is None or not self._conn.open:
        import pymysql
        from pymysql.cursors import DictCursor
        from core.config import DB_CONNECT_TIMEOUT
        self._conn = pymysql.connect(**self._cfg, cursorclass=DictCursor,
                                     connect_timeout=DB_CONNECT_TIMEOUT)
    return self._conn

# CRUD 方法改造:
# read_all_doc(): self._conn.cursor().execute("SELECT * FROM data_packages WHERE doc_type=%s", (doc_type,))
# create_doc(): INSERT INTO data_packages (id, doc_type, doc_data, status, created_at, updated_at) VALUES (...)
# update_doc(): UPDATE data_packages SET doc_data=%s, updated_at=NOW() WHERE id=%s
# delete_doc(): DELETE FROM data_packages WHERE id=%s
```

### 文件 9: `container_center/storage/config_store.py`

```python
# 删除: from .router import DatabaseRouter
# 构造函数: 改为接受 config dict
# 表: dispatch_commands
# SQL:
#   list_by_status: SELECT * FROM dispatch_commands WHERE status=%s ORDER BY priority DESC
#   create: INSERT INTO dispatch_commands (command_type, target_id, params, status, priority) VALUES (...)
#   update_status: UPDATE dispatch_commands SET status=%s WHERE id=%s
```

### 文件 10: `container_center/storage/index_store.py`

```python
# 删除: from .router import DatabaseRouter
# 构造函数: 改为接受 config dict
# 表: sync_logs, data_flow_logs, data_collection_records
# SQL:
#   INSERT: INSERT INTO sync_logs (action, package_id, detail) VALUES (...)
#   SELECT: SELECT * FROM sync_logs WHERE action=%s ORDER BY created_at DESC LIMIT %s
#   INSERT: INSERT INTO data_flow_logs (flow_type, source, target, status, detail) VALUES (...)
#   SELECT: SELECT * FROM data_flow_logs WHERE flow_type=%s AND created_at >= %s
#   INSERT: INSERT INTO data_collection_records (record_type, source_id, collected_at, data) VALUES (...)
```

### 文件 11: `container_center/storage/alert_store.py`

```python
# 删除: from .router import DatabaseRouter
# 构造函数: 改为接受 config dict
# 表: return_records, schedule_records
# SQL:
#   INSERT: INSERT INTO return_records (order_id, reason, returned_qty) VALUES (...)
#   SELECT: SELECT * FROM return_records WHERE order_id=%s
#   INSERT: INSERT INTO schedule_records (order_id, scheduled_date, machine_id) VALUES (...)
```

### 文件 12: `container_center/storage/redis_cache.py`

```python
# 确认无 SQLite 依赖，无需改动
```

### 文件 13: `container_center/__init__.py`

```python
# 删除:
# from .storage import DatabaseRouter
```

### 文件 14: `container_center/api/__init__.py`

```python
# 删除:
# from ..storage import DatabaseRouter
```

### 文件 15: `container_center/api/app.py`

```python
# 删除:
# from ..storage import DatabaseRouter

# ContainerCenter 初始化改为:
# self._cc = ContainerCenter(CONTAINER_MYSQL_CFG)
```

### 文件 16: `mobile_api_ai/storage_layer.py`

```python
# 删除 SQLite 相关代码块
# 在 create_storage() 中 MySQL 分支:
from core.config import CONTAINER_MYSQL_CFG, MYSQL_CFG

def create_storage(config):
    storage_type = config.get('type', 'mysql')
    if storage_type == 'mysql':
        db_name = config.get('db_name', 'container_center')
        cfg = CONTAINER_MYSQL_CFG if db_name == 'container_center' else MYSQL_CFG
        return MySQLStorage(cfg)
    # 删除: elif storage_type == 'sqlite': ...
```

### 文件 17: `mobile_api_ai/container_center_v5.py`

```python
# 删除 L34:
# from storage_mysql import MYSQL_CFG

# 改为:
from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT

# 将文件中所有 MYSQL_CFG 引用替换为 CONTAINER_MYSQL_CFG
```

### 文件 18: `mobile_api_ai/container_center_api.py` — _v4_doc_store (P0-8)

```python
# ========== 替换 L124-136 ==========
# 删除:
#     from container_center.storage import DatabaseRouter, DocumentStore, IndexStore, ConfigStore, AlertStore
#     _v4_data_dir = os.getenv('CC_DATA_DIR', os.path.join(BASE_DIR, 'data'))
#     _v4_router = DatabaseRouter(_v4_data_dir)
#     _v4_doc_store = DocumentStore(_v4_router)
#     _v4_idx_store = IndexStore(_v4_router)
#     _v4_cfg_store = ConfigStore(_v4_router)
#     _v4_alt_store = AlertStore(_v4_router)

# 改为:
from core.config import CONTAINER_MYSQL_CFG
# T02 已改造 document_store.py 为接受 config dict
_v4_doc_store = DocumentStore(CONTAINER_MYSQL_CFG)
_v4_idx_store = IndexStore(CONTAINER_MYSQL_CFG)
_v4_cfg_store = ConfigStore(CONTAINER_MYSQL_CFG)
_v4_alt_store = AlertStore(CONTAINER_MYSQL_CFG)
# 删除 _v4_router = DatabaseRouter(...) 行
# 删除 init_api_bp 中的 _v4_router 参数
```

---

## 阶段三: T03 核心改造 (7 文件)

### 文件 19: `mobile_api_ai/app.py` — direct_report (L139-212)

```python
# ========== 完整替换 direct_report() 函数体 (L139-212) ==========

@app.route('/api/v1/report', methods=['POST'])
def direct_report():
    import json, os as _os
    from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
    import pymysql
    from pymysql.cursors import DictCursor

    body = request.get_json(silent=True)
    if body is None and request.data:
        body = json.loads(request.data.decode('utf-8'))
    if not body:
        return jsonify({'code': 400, 'message': '请求体必须是有效的JSON对象'})

    task_id = body.get('task_id') or body.get('package_id', 0)
    qty = body.get('quantity', 0)
    qualified = body.get('qualified', 0)
    hours = body.get('hours', 0)
    remark = body.get('remark', '')
    worker = body.get('worker', '')

    # ===== 单写 container_center (替换原 L156-210) =====
    conn = pymysql.connect(**CONTAINER_MYSQL_CFG, autocommit=False,
                           cursorclass=DictCursor,
                           connect_timeout=DB_CONNECT_TIMEOUT)
    try:
        cur = conn.cursor()

        # L159 替换: rowid→id, 表名→data_packages
        cur.execute("SELECT * FROM data_packages WHERE id=%s", (task_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({'code': 404, 'message': f'任务 {task_id} 不存在'})

        # 更新 content (不变)
        content = json.loads(row['content']) if isinstance(row['content'], str) else (row['content'] or {})
        content['completed_qty'] = content.get('completed_qty', 0) + qty
        content['qualified_qty'] = content.get('qualified_qty', 0) + qualified
        content['work_hours'] = content.get('work_hours', 0) + hours
        if worker:
            content['worker'] = worker

        planned = content.get('planned_qty', 0)
        content['status'] = '已完成' if content['completed_qty'] >= planned > 0 else '进行中'

        # L173 替换: content?,title?→content=%s,title=%s; rowid→id
        cur.execute(
            "UPDATE data_packages SET content=%s, title=%s, status=%s, updated_at=NOW() WHERE id=%s",
            (json.dumps(content, ensure_ascii=False),
             f"{content.get('process_name','')}:{content['completed_qty']}/{planned}",
             content['status'], task_id))

        # 记录日志
        cur.execute(
            "INSERT INTO sync_logs (action, package_id, detail, created_at) VALUES (%s,%s,%s,NOW())",
            ('REPORT', str(task_id), f"报工+{qty} {remark}"))
        conn.commit()
    except pymysql.err.OperationalError as e:
        conn.rollback()
        logger.error(f'[direct_report] MySQL异常: {e}')
        return jsonify({'code': 503, 'message': f'数据库异常: {str(e)}'})
    except Exception as e:
        conn.rollback()
        import traceback
        logger.error(f'[direct_report] 异常: {e}\n{traceback.format_exc()}')
        return jsonify({'code': 500, 'message': f'报工失败: {str(e)}'})
    finally:
        conn.close()

    # ===== 异步通知 8008 (替代原 L179-210 整个 MySQL 双写块) =====
    try:
        import requests
        _sync_url = _os.environ.get('SYNC_BRIDGE_URL', 'http://127.0.0.1:8008')
        _order_no = content.get('order_no', '') or row.get('related_order', '')
        _process_code = content.get('process_code', '')
        if not _process_code:
            from core.config import get_process_code
            _process_code = get_process_code(content.get('process_name', ''))
        requests.post(f'{_sync_url}/api/sync/report',
                      json={'task_id': task_id, 'order_no': _order_no,
                            'qty': qty, 'process_code': _process_code,
                            'status': content['status'], 'worker': worker,
                            'remark': remark},
                      timeout=5)
    except Exception:
        logger.warning('[direct_report] sync_bridge 通知失败（非致命）')

    return jsonify({'code': 0, 'message': f'报工成功: +{qty}', 'data': content})
```

### 文件 20: `mobile_api_ai/app.py` — scanner_report_api (L229-314)

```python
# ========== 替换 scanner_report_api() 中的 L257-297 ==========

# === 替换 L257-274: 容器中心写入 ===
# 原: requests.post(f'{CONTAINER_CENTER_URL}/api/sub-step/report', ...)
# 改: pymysql 直写 container_center

conn = pymysql.connect(**CONTAINER_MYSQL_CFG, autocommit=True,
                       cursorclass=DictCursor, connect_timeout=DB_CONNECT_TIMEOUT)
cur = conn.cursor()
cur.execute("""
    INSERT INTO data_packages (package_type, title, content, status,
                               related_order, related_process, created_at)
    VALUES (%s,%s,%s,%s,%s,%s,NOW())
""", ('scan_report', f"扫描报工:{_order_no}",
      json.dumps({'order_no': _order_no, 'step_name': _step_name,
                  'operator': _operator, 'quantity': _quantity}),
      'reported', _order_no, _step_name))
cur.close()
conn.close()

# === 替换 L284-297: 8008 同步 ===
# L296: logger.error → logger.warning
_sync_url = _os.environ.get('SYNC_BRIDGE_URL', 'http://127.0.0.1:8008')
try:
    resp = requests.post(f'{_sync_url}/api/sync/sub-step-report',
                         json={'order_no': _order_no, 'step_name': _step_name,
                               'process_code': _process_code,
                               'operator': _operator, 'quantity': _quantity},
                         timeout=10)
    if resp.status_code != 200:
        logger.warning(f'[scanner] sync_bridge 返回非200: {resp.status_code}')
except Exception as e:
    logger.warning(f'[scanner] sync_bridge 不可达: {e}')  # ← 改为 warning
```

### 文件 21: `mobile_api_ai/container_center_api.py` — 12 处 storage._conn

```python
# ========== 文件顶部新增 import ==========
from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
import pymysql
from pymysql.cursors import DictCursor

# ========== 12 处逐行替换 ==========

# === L760-770: hardcoded OPERATORS → SELECT ===
# 原:
#     OPERATORS = [
#         {'operator_id': 'OP001', 'name': '张三', ...},
#         ...
#     ]
#     @app.route('/api/operators', methods=['GET'])
#     def get_operators():
#         return jsonify({'code': 0, 'data': {'operators': OPERATORS}})

# 改:
@app.route('/api/operators', methods=['GET'])
def get_operators():
    try:
        conn = pymysql.connect(**CONTAINER_MYSQL_CFG, cursorclass=DictCursor,
                               connect_timeout=DB_CONNECT_TIMEOUT)
        cur = conn.cursor()
        cur.execute("SELECT operator_id, name, role, department, wechat FROM operators WHERE enabled=1 ORDER BY operator_id")
        operators = cur.fetchall()
        conn.close()
        return jsonify({'code': 0, 'data': {'operators': operators}})
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})

# === L864: dispatch 去重查询 ===
# 原:
#     cur_dedup = container_center.storage._conn.cursor()
#     cur_dedup.execute('SELECT id FROM cc_data_packages WHERE ...')
# 改:
conn = pymysql.connect(**CONTAINER_MYSQL_CFG, cursorclass=DictCursor,
                       connect_timeout=DB_CONNECT_TIMEOUT)
cur_dedup = conn.cursor()
cur_dedup.execute(
    'SELECT id FROM data_packages WHERE related_order=%s AND process_name=%s AND target_operator_id=%s AND status!=%s LIMIT 1',
    (order_no, process, operator_id or '', 'completed'))
dup = cur_dedup.fetchone()
conn.close()

# === L891-893: dispatch 写入 ===
# 原:
#     cursor = container_center.storage._conn.cursor()
#     cursor.execute('UPDATE cc_data_packages SET ...')
#     container_center.storage._conn.commit()
# 改:
conn = pymysql.connect(**CONTAINER_MYSQL_CFG, autocommit=False,
                       cursorclass=DictCursor, connect_timeout=DB_CONNECT_TIMEOUT)
try:
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE data_packages SET process_code=%s, updated_at=NOW() WHERE id=%s',
        (process_code, pkg.package_id))
    conn.commit()
finally:
    conn.close()

# === L974: schedule/publish ===
# 原:
#     conn_flow = container_center.storage._conn
# 改:
conn_flow = pymysql.connect(**CONTAINER_MYSQL_CFG, cursorclass=DictCursor,
                            connect_timeout=DB_CONNECT_TIMEOUT)

# === L1044: schedule/publish 去重查询 ===
# 原:
#     conn = container_center.storage._conn
#     cursor = conn.cursor()
# 改:
conn = pymysql.connect(**CONTAINER_MYSQL_CFG, cursorclass=DictCursor,
                       connect_timeout=DB_CONNECT_TIMEOUT)
cursor = conn.cursor()

# === L2067: sub-step/report ===
# 改:
conn = pymysql.connect(**CONTAINER_MYSQL_CFG, autocommit=False,
                       cursorclass=DictCursor, connect_timeout=DB_CONNECT_TIMEOUT)

# === L2236: flow-map/sync ===
# 改:
conn = pymysql.connect(**CONTAINER_MYSQL_CFG, autocommit=False,
                       cursorclass=DictCursor, connect_timeout=DB_CONNECT_TIMEOUT)

# === L2253: flow-map/sync 查询 ===
# 改:
conn = pymysql.connect(**CONTAINER_MYSQL_CFG, cursorclass=DictCursor,
                       connect_timeout=DB_CONNECT_TIMEOUT)

# === L2274: sub-step/rollback ===
# 改:
conn = pymysql.connect(**CONTAINER_MYSQL_CFG, autocommit=False,
                       cursorclass=DictCursor, connect_timeout=DB_CONNECT_TIMEOUT)

# === L2320: sub-step/repair-mysql ===
# 改:
conn = pymysql.connect(**CONTAINER_MYSQL_CFG, cursorclass=DictCursor,
                       connect_timeout=DB_CONNECT_TIMEOUT)

# === L2333: sub-step/repair-mysql 去重查询 ===
# 改:
conn = pymysql.connect(**CONTAINER_MYSQL_CFG, cursorclass=DictCursor,
                       connect_timeout=DB_CONNECT_TIMEOUT)

# === L2368: operators (DB) ===
# 改:
conn = pymysql.connect(**CONTAINER_MYSQL_CFG, cursorclass=DictCursor,
                       connect_timeout=DB_CONNECT_TIMEOUT)
```

### 文件 22: `mobile_api_ai/container_center_api.py` — P0-9 process_id (L1970)

```python
# ========== 替换 L1968-1970 ==========
# 原:
#     advanced = False
#     try:
#         proc = container_center.storage.get_process_record(process_id)  # NameError!

# 改:
advanced = False
try:
    conn = pymysql.connect(**CONTAINER_MYSQL_CFG, cursorclass=DictCursor,
                           connect_timeout=DB_CONNECT_TIMEOUT)
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM data_packages WHERE related_order=%s AND related_process=%s LIMIT 1",
        (order_no, step_name))
    row = cur.fetchone()
    conn.close()
    if row:
        process_id = row['id']
        proc = container_center.storage.get_process_record(process_id)
        if proc:
            # 原有 advanced 逻辑...
            pass
    else:
        logger.warning(f'[api_create_sub_step] 未找到 process_record: {order_no}/{step_name}')
except Exception as e:
    logger.warning(f'[api_create_sub_step] 读取 process_record 失败: {e}')
```

### 文件 23: `mobile_api_ai/container_center_api.py` — P0-10 mysql_error (L2310)

```python
# ========== 替换 L2307-2311 ==========
# 原:
#     return success(data={
#         'order_no': order_no, 'step_name': step_name,
#         'remaining_qty': remaining_qty,
#         'mysql_synced': mysql_error is None,    # NameError!
#         'mysql_error': mysql_error              # NameError!
#     })

# 改:
return success(data={
    'order_no': order_no,
    'step_name': step_name,
    'remaining_qty': remaining_qty,
    # mysql_synced/mysql_error 已移除（8008 异步同步，非实时）
})
```

### 文件 24: `mobile_api_ai/dispatch_center.py` — MYSQL_CFG (L63-70)

```python
# ========== 替换 L63-70 ==========
# 删除:
# MYSQL_CFG = {
#     'host': os.environ.get('MYSQL_HOST', '127.0.0.1'),
#     'port': int(os.environ.get('MYSQL_PORT', 3306)),
#     'user': os.environ.get('MYSQL_USER', 'root'),
#     'password': os.environ.get('MYSQL_PASSWORD', '88888888'),  # ← 硬编码
#     'database': os.environ.get('MYSQL_DATABASE', 'steel_belt'),
#     'charset': 'utf8mb4',
# }

# 改为:
from core.config import MYSQL_CFG, CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
```

### 文件 25: `mobile_api_ai/dispatch_center.py` — L1505 SQLite→MySQL

```python
# ========== 替换 L1499-1529 ==========
# 删除原 SQLite 连接块:
#     cc = _get_client()
#     if cc and hasattr(cc, 'storage') and cc.storage:
#         db_path = DB_PATHS['container_center']
#         if os.path.exists(db_path):
#             import sqlite3
#             conn = sqlite3.connect(db_path)
#             ...

# 改为:
try:
    conn = pymysql.connect(**CONTAINER_MYSQL_CFG, cursorclass=DictCursor,
                           connect_timeout=DB_CONNECT_TIMEOUT)
    try:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT process_name FROM dispatch_commands WHERE process_name IS NOT NULL AND process_name != ''")
        for row in cur.fetchall():
            process_names.add(row['process_name'])
        cur.execute("SELECT DISTINCT related_process FROM data_packages WHERE related_process IS NOT NULL AND related_process != ''")
        for row in cur.fetchall():
            process_names.add(row['related_process'])
    finally:
        conn.close()
except Exception as e:
    logger.warning(f'[process-names] 从容器中心获取工序失败: {e}')
```

### 文件 26: `mobile_api_ai/dispatch_center.py` — L5308 SQLite→MySQL

```python
# ========== 替换 L5299-5330 ==========
# 删除原 SQLite 连接块:
#     from core.config import DB_PATHS
#     import sqlite3
#     db_path = DB_PATHS['wechat_container']
#     if not os.path.exists(db_path): return analysis
#     conn = sqlite3.connect(db_path)
#     ...

# 改为:
try:
    conn = pymysql.connect(**CONTAINER_MYSQL_CFG, cursorclass=DictCursor,
                           connect_timeout=DB_CONNECT_TIMEOUT)
    try:
        cur = conn.cursor()

        # 表1: data_flow_logs
        cur.execute("SELECT event_type, COUNT(*) as count FROM data_flow_logs GROUP BY event_type ORDER BY count DESC")
        analysis['data_flow_events'] = [{'event_type': r['event_type'], 'count': r['count']} for r in cur.fetchall()]

        # 表2: dispatch_commands
        cur.execute("SELECT status, COUNT(*) as count FROM dispatch_commands GROUP BY status")
        analysis['dispatch_commands'] = [{'status': r['status'], 'count': r['count']} for r in cur.fetchall()]

        # 表3: data_collection_records
        cur.execute("SELECT data_type, COUNT(*) as count FROM data_collection_records GROUP BY data_type")
        analysis['data_collection'] = [{'data_type': r['data_type'], 'count': r['count']} for r in cur.fetchall()]

        # 表4: sync_logs
        cur.execute("SELECT action, COUNT(*) as count FROM sync_logs GROUP BY action")
        analysis['sync_operations'] = [{'action': r['action'], 'count': r['count']} for r in cur.fetchall()]

        # 汇总 (保持不变)
        total_events = sum(item['count'] for item in analysis['data_flow_events'])
        total_commands = sum(item['count'] for item in analysis['dispatch_commands'])
        total_collections = sum(item['count'] for item in analysis['data_collection'])
        total_sync = sum(item['count'] for item in analysis['sync_operations'])

        analysis['summary'] = {
            'total_events': total_events,
            'total_commands': total_commands,
            'total_collections': total_collections,
            'total_sync_operations': total_sync,
            'health_score': calculate_health_score(total_events, analysis['dispatch_commands'])
        }
    finally:
        conn.close()
except Exception as e:
    logger.error(f'[轮询分析] 数据分析异常: {e}')
```

### 文件 27: `mobile_api_ai/api/process_v2.py` (L112-185)

```python
# ========== 完整替换 report_progress() 函数体 (L89-195) ==========

@bp.route('/<int:record_id>/report', methods=['POST'])
def report_progress(record_id):
    import json
    from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
    import pymysql
    from pymysql.cursors import DictCursor

    body = request.get_json(silent=True) or {}
    qty = body.get('quantity', 0)
    qualified = body.get('qualified', 0)
    hours = body.get('hours', 0)
    remark = body.get('remark', '')
    worker = body.get('worker', '')

    # ===== 单写 container_center =====
    conn = pymysql.connect(**CONTAINER_MYSQL_CFG, autocommit=False,
                           cursorclass=DictCursor,
                           connect_timeout=DB_CONNECT_TIMEOUT)
    try:
        cur = conn.cursor()

        # 查询 data_packages (L113+L117 合并为一条 MySQL 查询)
        cur.execute("SELECT * FROM data_packages WHERE id=%s", (str(record_id),))
        row = cur.fetchone()
        if not row:
            return fail(message=f'任务不存在: id={record_id}', code=404)

        content = json.loads(row['content']) if isinstance(row['content'], str) else (row['content'] or {})
        content['completed_qty'] = content.get('completed_qty', 0) + qty
        content['qualified_qty'] = content.get('qualified_qty', 0) + qualified
        content['work_hours'] = content.get('work_hours', 0) + hours
        if worker:
            content['worker'] = worker

        planned = content.get('planned_qty', 0)
        content['status'] = '已完成' if content['completed_qty'] >= planned > 0 else '进行中'

        # UPDATE (L138 替换)
        cur.execute(
            "UPDATE data_packages SET content=%s, title=%s, status=%s, updated_at=NOW() WHERE id=%s",
            (json.dumps(content, ensure_ascii=False),
             f"{content.get('process_name','')}:{content['completed_qty']}/{planned}",
             content['status'], str(record_id)))

        # INSERT sync_logs (L142 不变)
        cur.execute(
            "INSERT INTO sync_logs (action, package_id, detail, created_at) VALUES (%s,%s,%s,NOW())",
            ('REPORT', str(record_id), f"报工+{qty} {remark}"))

        conn.commit()  # L144 修正
    except Exception as e:
        conn.rollback()
        import traceback
        logger.error(f'[process_v2] 报工失败: {e}\n{traceback.format_exc()}')
        return fail(message=f'报工失败: {str(e)}', code=500)
    finally:
        conn.close()

    # ===== 异步通知 8008 (替代原 L147-185) =====
    try:
        import requests, os
        _sync_url = os.environ.get('SYNC_BRIDGE_URL', 'http://127.0.0.1:8008')
        _order_no = content.get('order_no', '') or row.get('related_order', '')
        _process_code = content.get('process_code', '')
        requests.post(f'{_sync_url}/api/sync/report',
                      json={'task_id': record_id, 'order_no': _order_no,
                            'qty': qty, 'process_code': _process_code,
                            'status': content['status'], 'worker': worker,
                            'remark': remark},
                      timeout=5)
    except Exception:
        logger.warning('[process_v2] sync_bridge 通知失败（非致命）')

    return success(data=content)
```

### 文件 28: `mobile_api_ai/sync_bridge.py`

```python
# ========== 替换 L12-13 ==========
# 原: from storage_mysql import MYSQL_CFG as _STORAGE_MYSQL_CFG
#     MYSQL_CFG = _STORAGE_MYSQL_CFG  # ← 指向 container_center (错误!)
# 改:
from core.config import MYSQL_CFG, CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
# MYSQL_CFG → steel_belt (写入目标)
# CONTAINER_MYSQL_CFG → container_center (读取源)

# ========== 替换 _get_container_storage (L45-51) ==========
# 原:
#     from storage_layer import StorageFactory, StorageType
#     return StorageFactory.get_instance(StorageType.SQLITE)
# 改:
def _get_container_conn():
    return pymysql.connect(**CONTAINER_MYSQL_CFG, cursorclass=DictCursor,
                          connect_timeout=DB_CONNECT_TIMEOUT)

# ========== 替换 _sync_to_container_db 中的 SQLite 操作 ==========
# 原:
#     storage = _get_container_storage()
#     records = storage.get_process_records(search=order_no)
# 改:
def _sync_to_container_db(order_no, status_key, plan_start=None, plan_end=None, schedule_days=None):
    conn = _get_container_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM data_packages WHERE JSON_EXTRACT(content, '$.order_no')=%s", (order_no,))
        records = list(cur.fetchall())
        for record in records:
            if record.get('order_no') == order_no:
                record['status'] = status_key
                record['updated_at'] = datetime.now().isoformat()
                cur.execute(
                    "UPDATE data_packages SET content=%s, status=%s, updated_at=NOW() WHERE id=%s",
                    (json.dumps(record), status_key, record['id']))
                logger.info('[SyncBridge->容器中心] 工单 %s 状态更新为 %s', order_no, status_key)
                break
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.warning('[SyncBridge->容器中心] 同步失败: %s', e)
    finally:
        conn.close()

# === _get_mysql_connection 不变，但 MYSQL_CFG 已改为指向 steel_belt ===
# === _sync_to_mysql 不变，自动写入 steel_belt ===
```

### 文件 29: `mobile_api_ai/dispatch_center/schedule_routes.py` (L1115-1123)

```python
# ========== 替换 L1115-1123 ==========
# 原: 内联 pymysql.connect(...)
#     conn = pymysql.connect(
#         host=os.getenv('MYSQL_HOST', 'localhost'),
#         ...
#         database=os.getenv('CONTAINER_MYSQL_DATABASE','container_center'),  # ← 连错库
#     )

# 改:
from core.config import MYSQL_CFG, DB_CONNECT_TIMEOUT

def _query_mysql_workorders(status=None):
    try:
        import pymysql
        from pymysql.cursors import DictCursor
        conn = pymysql.connect(**MYSQL_CFG, cursorclass=DictCursor,
                               connect_timeout=DB_CONNECT_TIMEOUT)
        c = conn.cursor()
        query = """SELECT pr.* FROM process_records pr
                   JOIN production_orders po ON pr.production_id = po.id
                   WHERE po.order_no IS NOT NULL AND po.order_no != ''"""
        params = []
        if status:
            query += " AND pr.status = %s"
            params.append(status)
        query += " ORDER BY pr.created_at DESC LIMIT 200"
        c.execute(query, params)
        result = c.fetchall()
        conn.close()
        return result
    except Exception as e:
        logger.error(f'[_query_mysql_workorders] 查询失败: {e}')
        return []
```

### 文件 30: `server_launcher.py`

```python
# ========== 保留 sync_bridge 启动项 ==========
# 确认以下配置存在:
# {'name': 'Sync Bridge', 'script': 'mobile_api_ai/sync_bridge.py',
#  'cwd': 'mobile_api_ai', 'port': 8008, ...}

# ========== 移除硬编码 API Key (L455) ==========
# 原: 'env': {'WECHAT_CLOUD_API_KEY': 'WkQ9-8X7Z-3K2M-5P6L'}
# 改: 'env': {'WECHAT_CLOUD_API_KEY': os.environ.get('WECHAT_CLOUD_API_KEY', '')}
```

---

## 阶段四: T04 同步处理器 (12 文件)

### 文件 31: `mobile_api_ai/sync/__init__.py`

```python
# ========== 新增内容 ==========
from contextlib import contextmanager
import pymysql
from pymysql.cursors import DictCursor
from core.config import MYSQL_CFG, CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT

@contextmanager
def mysql_cursor():
    """steel_belt 读写上下文（自动 commit/rollback）"""
    conn = pymysql.connect(**MYSQL_CFG, autocommit=False,
                           cursorclass=DictCursor,
                           connect_timeout=DB_CONNECT_TIMEOUT)
    try:
        yield conn.cursor()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

@contextmanager
def container_cursor():
    """container_center 读写上下文（自动 commit/rollback）"""
    conn = pymysql.connect(**CONTAINER_MYSQL_CFG, autocommit=False,
                           cursorclass=DictCursor,
                           connect_timeout=DB_CONNECT_TIMEOUT)
    try:
        yield conn.cursor()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

### 文件 32: `sync/handlers/worker_handler.py`

```python
# ========== 替换 ==========
# 删除: import sqlite3
# 删除: _cs_cursor() 函数
# 改为:
from .. import container_cursor

def handle_worker_created(data):
    with container_cursor() as cur:
        cur.execute("""
            INSERT INTO workers (enterprise_id, name, phone, role, department, status, sync_at)
            VALUES (%s,%s,%s,%s,%s,%s,NOW())
            ON DUPLICATE KEY UPDATE name=VALUES(name), phone=VALUES(phone),
                                    status=VALUES(status), sync_at=NOW()
        """, (data['userid'], data['name'], data.get('mobile', ''),
              data.get('position', '员工'), data.get('main_department', ''),
              'active'))
```

### 文件 33: `sync/handlers/sub_step_handler.py`

```python
# ========== 替换 ==========
# 删除: import sqlite3
# 删除: _cs_cursor(), _container_cursor() 函数
# 改为:
from .. import mysql_cursor, container_cursor

# steel_belt 操作: process_sub_steps
def handle_sub_step_completed(data):
    with mysql_cursor() as cur:
        cur.execute("""
            INSERT INTO process_sub_steps (process_record_id, step_name, completed_qty, status)
            VALUES (%s,%s,%s,%s)
        """, (data['process_id'], data['step_name'], data['quantity'], 'completed'))

# container_center 操作: workers 关联
def _get_worker(enterprise_id):
    with container_cursor() as cur:
        cur.execute("SELECT * FROM workers WHERE enterprise_id=%s", (enterprise_id,))
        return cur.fetchone()
```

### 文件 34: `sync/handlers/quality_handler.py`

```python
# ========== 替换 ==========
# 删除: import sqlite3
# 改为:
from .. import mysql_cursor

def handle_quality_recorded(data):
    with mysql_cursor() as cur:
        cur.execute("""
            UPDATE process_records SET quality_status=%s, defect_qty=%s,
            inspected_at=NOW() WHERE id=%s
        """, (data['quality_status'], data.get('defect_qty', 0), data['record_id']))
```

### 文件 35: `sync/handlers/order_handler.py`

```python
# ========== 替换 ==========
# 删除: import sqlite3
# 改为:
from .. import mysql_cursor

def handle_order_updated(data):
    with mysql_cursor() as cur:
        cur.execute("""
            INSERT INTO orders (order_no, product_name, customer_name, quantity, unit, status)
            VALUES (%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE status=VALUES(status), updated_at=NOW()
        """, (data['order_no'], data['product_name'], data['customer_name'],
              data['quantity'], data['unit'], data['status']))
```

### 文件 36: `sync/handlers/attendance_handler.py`

```python
# ========== 替换 ==========
# 删除: import sqlite3
# 改为:
from .. import container_cursor

def handle_attendance_recorded(data):
    with container_cursor() as cur:
        cur.execute("""
            INSERT INTO attendance (worker_id, date, check_in, status)
            VALUES (%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE check_in=VALUES(check_in), status=VALUES(status)
        """, (data['worker_id'], data['date'], data.get('check_in'), data.get('status', 'present')))
```

### 文件 37: `mobile_api_ai/sync/sync_log.py`

```python
# ========== 替换 ==========
# 删除: import sqlite3
# 删除: sqlite3.connect(db_path)
# 改为:
from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
import pymysql
from pymysql.cursors import DictCursor

def log_sync(action, package_id, detail):
    try:
        conn = pymysql.connect(**CONTAINER_MYSQL_CFG, cursorclass=DictCursor,
                               connect_timeout=DB_CONNECT_TIMEOUT)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO sync_logs (action, package_id, detail, created_at) VALUES (%s,%s,%s,NOW())",
            (action, str(package_id), detail))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f'[sync_log] 写入失败: {e}')
```

### 文件 38: `mobile_api_ai/wechat_message_store.py`

```python
# ========== 替换 ==========
# 删除: import sqlite3
# 删除: sqlite3.connect(db_path)
# 改为:
from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
import pymysql
from pymysql.cursors import DictCursor

class WechatMessageStore:
    def __init__(self, db_dir=None):
        pass  # 不再需要 db_dir

    def _get_conn(self):
        conn = pymysql.connect(**CONTAINER_MYSQL_CFG, cursorclass=DictCursor,
                               connect_timeout=DB_CONNECT_TIMEOUT)
        self._ensure_table(conn)
        return conn

    def _ensure_table(self, conn):
        from datetime import datetime
        now = datetime.now()
        table_name = f'wechat_messages_{now.year}_{now.month:02d}'
        cur = conn.cursor()
        cur.execute(f'''CREATE TABLE IF NOT EXISTS `{table_name}` (
            id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            msg_id VARCHAR(64), from_user VARCHAR(64), to_user VARCHAR(64),
            msg_type VARCHAR(32), content TEXT, raw_xml TEXT, response TEXT,
            status VARCHAR(32) DEFAULT 'received',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_msg_id (msg_id), INDEX idx_from_user (from_user),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
        cur.close()
        return table_name

    def save_message(self, data):
        conn = self._get_conn()
        try:
            table_name = self._ensure_table(conn)
            cur = conn.cursor()
            cur.execute(f"""INSERT INTO `{table_name}`
                (msg_id, from_user, msg_type, content, status) VALUES (%s,%s,%s,%s,%s)""",
                (data.get('msg_id'), data.get('from_user'),
                 data.get('msg_type'), json.dumps(data), 'received'))
            conn.commit()
            return cur.lastrowid
        except Exception as e:
            logger.warning(f'[wechat_message] 保存失败: {e}')
        finally:
            conn.close()

    def get_messages(self, from_user=None, limit=100):
        conn = self._get_conn()
        try:
            table_name = self._ensure_table(conn)
            cur = conn.cursor()
            if from_user:
                cur.execute(f"SELECT * FROM `{table_name}` WHERE from_user=%s ORDER BY created_at DESC LIMIT %s",
                            (from_user, limit))
            else:
                cur.execute(f"SELECT * FROM `{table_name}` ORDER BY created_at DESC LIMIT %s", (limit,))
            return cur.fetchall()
        finally:
            conn.close()
```

### 文件 39: `mobile_api_ai/operation_log.py`

```python
# ========== 替换 ==========
# 删除: import sqlite3
# 删除: sqlite3.connect(self.db_path)
# 改为:
from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
import pymysql
from pymysql.cursors import DictCursor

class OperationLogDB:
    def __init__(self, db_path=None):
        pass

    def _get_conn(self):
        return pymysql.connect(**CONTAINER_MYSQL_CFG, cursorclass=DictCursor,
                               connect_timeout=DB_CONNECT_TIMEOUT)

    def log_operation(self, data):
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO operation_logs (operation_type, operator_id, target_type, target_id, detail) VALUES (%s,%s,%s,%s,%s)",
                (data.get('type'), data.get('operator_id'), data.get('target_type'),
                 data.get('target_id'), json.dumps(data.get('detail', {}))))
            conn.commit()
        finally:
            conn.close()
```

### 文件 40: `mobile_api_ai/cloud_backup.py`

```python
# 🗑️ 整个文件废弃/删除
```

### 文件 41: `mobile_api_ai/inventory_api_server.py`

```python
# 删除本地 MYSQL_CFG 定义
# 改为:
from core.config import MYSQL_CFG, DB_CONNECT_TIMEOUT
```

### 文件 42: `mobile_api_ai/mysql_storage.py`

```python
# T01 已完成, 确认:
from core.config import MYSQL_CFG, DB_CONNECT_TIMEOUT
```

---

## 阶段五: T05 清理验证 (10 文件)

### 文件 43: `server_launcher.py` — 最终清理

```python
# 确认: 移除所有硬编码密码和 API Key
# 确认: 所有服务的 env 传递一致
```

### 文件 44: `core/config.py` — 最终清理

```python
# 确认: DB_PATHS 中已移除所有 SQLite 业务路径
# 确认: MYSQL_CFG + CONTAINER_MYSQL_CFG 正确配置
```

### 文件 45: `.env.example` — 最终同步

```
CONTAINER_MYSQL_DATABASE=container_center
DB_CONNECT_TIMEOUT=5
MYSQL_PASSWORD=your_password_here
```

### 文件 46: `CHANGELOG.md`

```
## [v3.x] 2026-05-30 — MySQL 直写迁移
- 所有业务数据读写改为 MySQL (steel_belt + container_center)
- 废弃 Router (12 SQLite 文件) 和 sync_bridge SQLite 桥接
- sync_bridge 改为 MySQL→MySQL 8008 桥接
- 保留 SQLite: SchedulerManager, face_checkin
```

### 文件 47-51: 5 个 scripts 归档

```bash
mv _full_order_query.py scripts/archive/
mv _diagnose_order_api.py scripts/archive/
mv _diagnose_order_003.py scripts/archive/
mv _diag_simple.py scripts/archive/
mv query_order_003.py scripts/archive/
```

### 文件 52: `tests/test_migration.py` (新增)

```python
"""
7 个验证测试:
1. test_direct_report: 报工写入 container_center → 8008 通知 → steel_belt 同步
2. test_dispatch_query: L5308 轮询分析聚合正确
3. test_process_names: L1505 工序名查询正确
4. test_worker_sync: handler 事件处理
5. test_wechat_message: 动态建表 + 写入
6. test_rollback_sub_step: P0-10 不崩溃
7. test_process_v2: 报工 + 8008 通知
"""
import unittest
import pymysql
from core.config import MYSQL_CFG, CONTAINER_MYSQL_CFG

class TestMigration(unittest.TestCase):
    def test_connections(self):
        """两个库均可连接"""
        conn1 = pymysql.connect(**MYSQL_CFG)
        conn1.close()
        conn2 = pymysql.connect(**CONTAINER_MYSQL_CFG)
        conn2.close()

    def test_direct_report(self):
        """报工流程端到端"""
        # 写入 container_center
        conn = pymysql.connect(**CONTAINER_MYSQL_CFG, autocommit=False,
                               cursorclass=pymysql.cursors.DictCursor)
        cur = conn.cursor()
        # ... 模拟报工 ...
        conn.rollback()  # 测试后回滚
        conn.close()

    # ... (其余 5 个测试)
```

---

## 实施顺序

```
T01 (配置 5文件) ──→ T02 (Router 12文件) ──→ T03 (核心 7文件)
                         │                        │
                         └──→ T04 (Handler 12文件) ──→ T05 (清理 10文件)
```

**每阶段完成后重启对应服务验证, 确认无报错再继续。**

---

## 不可改

| 位置 | 原因 |
|------|------|
| dispatch_center.py L4496/4510/4523 | SchedulerManager — 调度器本地配置 |
| face_checkin/__init__.py | 人脸签到独立模块 |
