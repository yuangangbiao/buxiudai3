"""
MySQL 兼容路由器 — 替代已废弃的 SQLite DatabaseRouter
为 document_store/config_store/index_store/alert_store 提供相同的接口
"""
from contextlib import contextmanager
from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
from core.db import get_direct_connection


class MySQLRouter:
    """兼容 DatabaseRouter 接口的 MySQL 连接器"""

    def __init__(self, config=None):
        self._cfg = config or CONTAINER_MYSQL_CFG

    @contextmanager
    def get_db_cursor(self, doc_type):
        conn = get_direct_connection(**self._cfg,
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
    def get_db_cursor_by_name(self, db_name):
        with self.get_db_cursor(None) as cur:
            yield cur

    def get_all_db_names(self):
        return ['default']

    def resolve_db_name(self, doc_type):
        return 'default'
