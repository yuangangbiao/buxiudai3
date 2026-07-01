"""
自动数据库表结构同步模块

核心机制：
在数据写入事件前自动检查目标表/列是否存在，
若不存在则自动建表/加列，确保写入不会因缺少表或字段而失败。

适用于 MySQL 和 SQLite 双后端。

额外提供 SafeCursor 包装类，可无侵入地嵌入到 get_db_cursor() 上下文中，
自动拦截 cursor.execute() 的 INSERT/UPDATE 调用并触发 auto_ensure_schema。
"""

import logging
import re
import threading
from collections import OrderedDict
from typing import Dict, Any, Set, Optional, Tuple

logger = logging.getLogger(__name__)

_SCHEMA_CACHE_MAX = 500
_schema_cache: OrderedDict = OrderedDict()
_schema_lock = threading.Lock()

_TYPE_MAP = {
    int: ('INTEGER', 'INT'),
    float: ('REAL', 'DECIMAL(14,4)'),
    str: None,
    bool: ('INTEGER', 'TINYINT(1)'),
    type(None): ('TEXT', 'TEXT'),
}

_INSERT_FULL_RE = re.compile(
    r'^\s*INSERT\s+(?:OR\s+\w+\s+)?INTO\s+`?(\w+)`?\s*'
    r'\(([^)]+)\)\s*VALUES',
    re.I | re.S
)

_UPDATE_SET_RE = re.compile(
    r'^\s*UPDATE\s+`?(\w+)`?\s+SET\s+'
    r'(.+?)(?:\s+WHERE|\s+ORDER\s+|\s+LIMIT|\s*$)',
    re.I | re.S
)

_SET_COL_RE = re.compile(r'(?:^|[,\s]+)\s*`?(\w+)`?\s*=\s*(?:%s|\?)', re.I)


def _infer_sql_type(value: Any, is_sqlite: bool) -> str:
    if py_type := type(value):
        entry = _TYPE_MAP.get(py_type)
        if entry is not None:
            return entry[0] if is_sqlite else entry[1]
    if isinstance(value, (dict, list)):
        return 'TEXT'
    if isinstance(value, str):
        if is_sqlite:
            return 'TEXT'
        return 'VARCHAR(255)' if len(value) <= 255 else 'TEXT'
    return 'TEXT'


def _get_db_identity(conn) -> str:
    mod = type(conn).__module__
    if 'pymysql' in mod:
        try:
            return f"mysql:{conn.db}"
        except AttributeError:
            return f"mysql:{id(conn)}"
    elif 'sqlite3' in mod:
        try:
            return f"sqlite:{conn.database}"
        except AttributeError:
            return f"sqlite:{id(conn)}"
    return f"unknown:{id(conn)}"


def _validate_name(name: str) -> bool:
    return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name))


def _check_table_exists(cursor, table_name: str, is_sqlite: bool) -> bool:
    if is_sqlite:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    else:
        cursor.execute("SHOW TABLES LIKE %s", (table_name,))
    return cursor.fetchone() is not None


def _get_existing_columns(cursor, table_name: str, is_sqlite: bool) -> Set[str]:
    if is_sqlite:
        cursor.execute(f"PRAGMA table_info({table_name})")
        return {row[1] for row in cursor.fetchall()}
    else:
        cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
        rows = cursor.fetchall()
        if rows and isinstance(rows[0], dict):
            return {row['Field'] for row in rows}
        return {row[0] for row in rows}


def _create_table_ddl(ddl_conn, table_name: str, columns: Dict[str, str], is_sqlite: bool):
    col_defs = [f"`{name}` {col_type}" for name, col_type in columns.items()]
    if not is_sqlite:
        sql = f"CREATE TABLE IF NOT EXISTS `{table_name}` ({', '.join(col_defs)}) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
    else:
        sql = f"CREATE TABLE IF NOT EXISTS `{table_name}` ({', '.join(col_defs)})"
    cursor = ddl_conn.cursor()
    try:
        cursor.execute(sql)
        ddl_conn.commit()
        logger.info('auto-created table: %s with %d columns', table_name, len(columns))
    except Exception as e:
        ddl_conn.rollback()
        logger.error('failed to create table %s: %s', table_name, e)
    finally:
        cursor.close()


def _add_missing_columns_ddl(ddl_conn, table_name: str, missing: Dict[str, str], is_sqlite: bool):
    cursor = ddl_conn.cursor()
    added = []
    try:
        for col_name, col_type in missing.items():
            try:
                cursor.execute(f"ALTER TABLE `{table_name}` ADD COLUMN `{col_name}` {col_type}")
                added.append(col_name)
            except Exception as e:
                logger.warning('failed to add column %s to %s: %s', col_name, table_name, e)
        if added:
            ddl_conn.commit()
            logger.info('auto-added columns to %s: %s', table_name, ', '.join(added))
    except Exception as e:
        logger.error('error adding columns to %s: %s', table_name, e)
    finally:
        cursor.close()


def _open_ddl_connection(conn):
    mod = type(conn).__module__
    if 'pymysql' in mod:
        from core.db import get_direct_connection
        return get_direct_connection(
            host=conn.host, port=conn.port,
            user=conn.user, password=conn.password,
            database=conn.db, charset='utf8mb4',
        )
    elif 'sqlite3' in mod:
        import sqlite3
        return sqlite3.connect(conn.database, timeout=10)
    return None


def auto_ensure_schema(conn, table_name: str, data: Dict[str, Any]):
    """
    自动确保表结构包含所有数据字段

    在写入数据前调用，检查目标表和列是否存在。
    若表不存在则自动创建（含 id 自增主键），
    若列不存在则自动 ALTER TABLE ADD COLUMN。

    DDL 操作在独立连接上执行，不影响调用方当前事务。
    并发安全：内部使用线程锁保护，缓存上限 500 条目（LRU淘汰）。

    Args:
        conn: 数据库连接对象（pymysql.Connection 或 sqlite3.Connection）
        table_name: 目标表名
        data: 待写入的数据字典（字段名 → 值）
    """
    if not data or not table_name:
        return

    if not _validate_name(table_name):
        logger.warning('invalid table name: %s, skip auto-schema', table_name)
        return

    db_id = _get_db_identity(conn)
    cache_key = f"{db_id}:{table_name}"

    with _schema_lock:
        if cache_key in _schema_cache:
            _schema_cache.move_to_end(cache_key)
            return

    is_sqlite = 'sqlite3' in type(conn).__module__

    cursor = conn.cursor()
    try:
        table_exists = _check_table_exists(cursor, table_name, is_sqlite)
    finally:
        cursor.close()

    if not table_exists:
        primary_type = 'INTEGER PRIMARY KEY AUTOINCREMENT' if is_sqlite else 'INT PRIMARY KEY AUTO_INCREMENT'
        columns: Dict[str, str] = {}
        columns['id'] = primary_type
        for key, value in data.items():
            if key == 'id':
                continue
            columns[key] = _infer_sql_type(value, is_sqlite)

        ddl_conn = _open_ddl_connection(conn)
        if ddl_conn:
            try:
                _create_table_ddl(ddl_conn, table_name, columns, is_sqlite)
            finally:
                ddl_conn.close()
        with _schema_lock:
            _schema_cache[cache_key] = True
            while len(_schema_cache) > _SCHEMA_CACHE_MAX:
                _schema_cache.popitem(last=False)
        return

    cursor = conn.cursor()
    try:
        existing = _get_existing_columns(cursor, table_name, is_sqlite)
    finally:
        cursor.close()

    missing: Dict[str, str] = {}
    for key, value in data.items():
        if key == 'id':
            continue
        if key not in existing:
            missing[key] = _infer_sql_type(value, is_sqlite)

    if missing:
        ddl_conn = _open_ddl_connection(conn)
        if ddl_conn:
            try:
                _add_missing_columns_ddl(ddl_conn, table_name, missing, is_sqlite)
            finally:
                ddl_conn.close()

    with _schema_lock:
        _schema_cache[cache_key] = True
        while len(_schema_cache) > _SCHEMA_CACHE_MAX:
            _schema_cache.popitem(last=False)
    logger.debug('schema OK: %s (cached)', cache_key)


def clear_schema_cache():
    """清空表结构缓存（用于测试或强制重新检查）"""
    with _schema_lock:
        _schema_cache.clear()


def _build_data_from_sql(sql: str, params: Any) -> Optional[Tuple[str, Dict[str, Any]]]:
    """从 SQL 语句和参数中提取(表名, 字段名→值字典)，若无法提取返回 None"""

    # 裁剪 ON DUPLICATE KEY UPDATE 后缀（避免 VALUES 关键字歧义 + 额外参数干扰）
    clean_sql = re.sub(r'\s+ON\s+DUPLICATE\s+KEY\s+UPDATE\s+.+$', '', sql, flags=re.I)

    m = _INSERT_FULL_RE.match(clean_sql)
    if m:
        table = m.group(1)
        cols_str = m.group(2)
        cols = [c.strip().strip('`') for c in cols_str.split(',')]
        if cols and params is not None and isinstance(params, (tuple, list)):
            valid_cols = [c for c in cols if _validate_name(c)]
            data = {}
            # 仅取 INSERT 列数的参数（忽略 ON DUPLICATE KEY UPDATE 的额外参数）
            param_count = min(len(valid_cols), len(params))
            for i in range(param_count):
                data[valid_cols[i]] = params[i]
            return (table, data) if data else None
        return None

    m = _UPDATE_SET_RE.match(sql)
    if m:
        table = m.group(1)
        set_clause = m.group(2)
        set_cols = _SET_COL_RE.findall(set_clause)
        if set_cols and params is not None and isinstance(params, (tuple, list)):
            data = {}
            for i, col in enumerate(set_cols):
                if i < len(params) and _validate_name(col):
                    data[col] = params[i]
            return (table, data) if data else None
        return None

    return None


class SafeCursor:
    """
    Cursor 包装器，在 INSERT/UPDATE 执行前自动触发 auto_ensure_schema。

    用法：
        with get_db_cursor() as (cursor, conn):
            safe = SafeCursor(cursor, conn)
            safe.execute("INSERT INTO ...", (val1, val2))
            # 自动建表/加列，无需手动处理

    所有非 execute 的属性和方法自动透传给原始 cursor。
    """

    def __init__(self, cursor, conn):
        self._cursor = cursor
        self._conn = conn

    def execute(self, query, params=None):
        result = _build_data_from_sql(query, params)
        if result is not None:
            table_name, data = result
            try:
                auto_ensure_schema(self._conn, table_name, data)
            except Exception:
                pass
        if 'pymysql' in type(self._conn).__module__:
            query = query.replace('?', '%s')
        if params is not None:
            return self._cursor.execute(query, params)
        return self._cursor.execute(query)

    def executemany(self, query, seq_of_params):
        if seq_of_params and len(seq_of_params) > 0:
            result = _build_data_from_sql(query, seq_of_params[0])
            if result is not None:
                table_name, data = result
                try:
                    auto_ensure_schema(self._conn, table_name, data)
                except Exception:
                    pass
        if 'pymysql' in type(self._conn).__module__:
            query = query.replace('?', '%s')
        return self._cursor.executemany(query, seq_of_params)

    def __iter__(self):
        return iter(self._cursor)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._cursor.__exit__(exc_type, exc_val, exc_tb)

    def __getattr__(self, name):
        return getattr(self._cursor, name)
