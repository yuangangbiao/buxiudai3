# MySQL 直写迁移 — 量子化执行清单

## 阶段1: 配置 (1 文件改动)

```python
# core/config.py — 新增一个字典
CONTAINER_MYSQL_CFG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', ''),
    'database': os.getenv('CONTAINER_MYSQL_DATABASE', 'container_center'),
    'charset': 'utf8mb4',
}
```
```env
# .env — 加一行
CONTAINER_MYSQL_DATABASE=container_center
```

## 阶段2: 替换清单 (逐文件, 逐行)

### container_center_api.py

| 改什么 | 怎么改 |
|--------|--------|
| L124-136 _v4_doc_store | 删 DatabaseRouter → `pymysql(**CONTAINER_MYSQL_CFG)` |
| L760 OPERATORS硬编码 | → `SELECT operator_id,name,role FROM operators` |
| L864-2368 共12处 `storage._conn` | → `pymysql.connect(**CONTAINER_MYSQL_CFG)` |
| L865 `cc_data_packages` | → `data_packages` |
| L892 `cc_data_packages` | → `data_packages` |
| L1970 `process_id`未定义 | → `SELECT id FROM data_packages WHERE related_order=%s AND related_process=%s` |
| L2310 `mysql_error`未定义 | → 删除这两行返回值 |

### app.py

| 改什么 | 怎么改 |
|--------|--------|
| L158-210 整个块 | 删除。替换为: `pymysql(**CONTAINER_MYSQL_CFG)` → `UPDATE data_packages SET content=%s WHERE id=%s` → `INSERT sync_logs` → commit → `requests.post(8008/sync/report)` |
| L257-274 容器中心API调用 | 删除。替换为: `pymysql(**CONTAINER_MYSQL_CFG)` 直写 |
| L296 `logger.error` 静默 | → `logger.warning` |

### dispatch_center.py

| 改什么 | 怎么改 |
|--------|--------|
| L63-70 本地 MYSQL_CFG | 删除。→ `from core.config import MYSQL_CFG` |
| L1500-1517 sqlite3 读 | 删除。→ `pymysql(**CONTAINER_MYSQL_CFG)` 查 dispatch_commands + data_packages |
| L5300-5308 sqlite3 四表读 | 删除。→ `pymysql(**CONTAINER_MYSQL_CFG)` 分别查 |

### api/process_v2.py

| 改什么 | 怎么改 |
|--------|--------|
| L112-185 整个块 | 删除。替换为: 同 app.py 模式 — `pymysql(**CONTAINER_MYSQL_CFG)` → UPDATE+INSERT → commit → `requests.post(8008)` |
| L113 `%s?` | 随替换消失 |
| L138 SQL损坏 | 随替换消失 |
| L144 `None.commit()` | 随替换消失 |

### sync_bridge.py

| 改什么 | 怎么改 |
|--------|--------|
| L12-13 import | → `from core.config import MYSQL_CFG, CONTAINER_MYSQL_CFG` |
| L45-51 StorageFactory(SQLite) | → `pymysql(**CONTAINER_MYSQL_CFG)` |
| MYSQL_CFG 指向 | 从 container_center → steel_belt |

### sync/handlers/*.py (5个)

| 改什么 | 怎么改 |
|--------|--------|
| `sqlite3.connect(db_path)` | → `from .. import mysql_cursor` 或 `container_cursor` |

### 辅助模块 (3个)

| 文件 | 改什么 |
|------|--------|
| wechat_message_store.py | `sqlite3` → `pymysql(**CONTAINER_MYSQL_CFG)` |
| operation_log.py | `sqlite3` → `pymysql(**CONTAINER_MYSQL_CFG)` |
| schedule_routes.py L1115-1123 | 内联 pymysql → `from core.config import MYSQL_CFG` |

## 阶段3: 删除

| 文件 | 操作 |
|------|------|
| router.py | 删 |
| sync_bridge.py | 不删（改造为 MySQL→MySQL） |
| cloud_backup.py | 删 |
| 5个 _*.py scripts | 移到 archive/ |

## 不可动

| 位置 | 原因 |
|------|------|
| dispatch_center L4496/4510/4523 | SchedulerManager 本地配置，留 SQLite |
| face_checkin/__init__.py | 人脸签到独立模块 |

---

**总计: 19 个文件, 0 行解释。**
