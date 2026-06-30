# -*- coding: utf-8 -*-
"""
数据库模块 — 统一连接管理器过渡包

v3.0 重构:
  - 连接统一走 core.db (DB 类 → ConnectionPool → PooledConnection)
  - _database_legacy.py 只保留 init_db / ensure_*_indexes 等独特功能
  - 2026-06-09: 旧版 connection_pool.py 已彻底归档至 _archive/legacy_db/，
    同名 MySQLConnectionPool/PooledConnection 现仅在 core.db 中定义。
"""
# ── 统一连接入口 (core.db) ──
from core.db import (
    get_connection, get_connection_context,
    MySQLConnectionPool, PooledConnection, reload_db_config,
)

# ── 配置 ──
from .config import _get_db_config, MYSQL_CONFIG

# ── 工具函数 ──
from .utils_db import (
    _validate_sql_identifier, _safe_table_name,
    generate_order_no, generate_shipment_no,
    log_status_change,
)

# ── 独特遗留符号 (仅在 _database_legacy.py 中定义) ──
from ._database_legacy import init_db, ensure_unique_indexes, ensure_performance_indexes
