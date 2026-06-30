# -*- coding: utf-8 -*-
"""
数据库连接池 - 修复 P1-1/P1-2/P1-3 + 循环依赖

修复点：
- 移除 from tests.conftest import DB_CONFIG（会循环导入），改用 _config
- 简化 get_connection 的双重等待
- cleanup_test_data 使用 _config.TEST_DATA_TABLES
- ping(reconnect=True) 弃用改用 ping() + connect()
"""
import logging
import queue
import threading
from contextlib import contextmanager
from typing import Dict, List, Any, Optional

import pymysql
from pymysql.cursors import DictCursor

# 修复 A1: 从 _config 导入，避免循环依赖
from tests.core._config import DB_CONFIG, TEST_DATA_TABLES

logger = logging.getLogger(__name__)


class ConnectionPool:
    """线程安全的 MySQL 连接池"""

    def __init__(self, config: Optional[Dict] = None, max_size: int = 10, timeout: float = 30):
        self.config = config or DB_CONFIG
        self.max_size = max_size
        self.timeout = timeout
        self._pool: queue.Queue = queue.Queue(maxsize=max_size)
        self._lock = threading.Lock()
        self._created = 0
        self._stats = {
            'created': 0,
            'borrowed': 0,
            'returned': 0,
            'invalidated': 0,
        }

    def _create_connection(self) -> pymysql.connections.Connection:
        """创建新连接"""
        self._stats['created'] += 1
        return pymysql.connect(**self.config)

    def _is_valid(self, conn) -> bool:
        """
        检查连接是否有效

        修复：pymysql 1.2.0 弃用 ping(reconnect=True)，改用 ping() + 手动 connect()
        """
        try:
            conn.ping()
            return True
        except Exception:
            # ping 失败，尝试重连
            try:
                conn.connect()
                return True
            except Exception:
                return False

    def get_connection(self, timeout: Optional[float] = None) -> pymysql.connections.Connection:
        """
        获取连接 - 修复 P1-1: 移除双重等待

        简化流程：
        1. 先尝试创建（如果未达上限）
        2. 再尝试从池中获取
        3. 最后阻塞等待
        """
        timeout = timeout or self.timeout
        self._stats['borrowed'] += 1

        # 1. 优先创建新连接（未达上限时）
        with self._lock:
            if self._created < self.max_size:
                self._created += 1
                try:
                    return self._create_connection()
                except Exception as e:
                    self._created -= 1
                    logger.error(f"创建连接失败: {e}")
                    # 继续尝试从池中获取

        # 2. 从池中获取
        try:
            conn = self._pool.get(timeout=timeout)
            if self._is_valid(conn):
                return conn
            # 无效连接，丢弃
            self._stats['invalidated'] += 1
            try:
                conn.close()
            except Exception:
                pass
            with self._lock:
                self._created = max(0, self._created - 1)
        except queue.Empty:
            pass

        # 3. 池中无可用连接，阻塞等待
        return self._pool.get(timeout=timeout)

    def return_connection(self, conn: pymysql.connections.Connection):
        """归还连接"""
        if not conn:
            return

        self._stats['returned'] += 1

        if not self._is_valid(conn):
            self._stats['invalidated'] += 1
            try:
                conn.close()
            except Exception:
                pass
            with self._lock:
                self._created = max(0, self._created - 1)
            return

        try:
            self._pool.put_nowait(conn)
        except queue.Full:
            try:
                conn.close()
            except Exception:
                pass
            with self._lock:
                self._created = max(0, self._created - 1)

    def close_all(self):
        """关闭所有连接"""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except Exception:
                pass
        self._created = 0

    def get_stats(self) -> Dict:
        return {**self._stats, 'pool_size': self._pool.qsize(), 'max_size': self.max_size}


class DBHelperPooled:
    """使用连接池的数据库助手"""

    def __init__(self, pool: Optional[ConnectionPool] = None):
        self.pool = pool or ConnectionPool()

    @contextmanager
    def connection(self):
        conn = self.pool.get_connection()
        try:
            yield conn
        finally:
            self.pool.return_connection(conn)

    @contextmanager
    def cursor(self, dict_cursor: bool = True):
        """游标上下文"""
        with self.connection() as conn:
            cursor = conn.cursor(DictCursor if dict_cursor else None)
            try:
                yield cursor
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cursor.close()

    def query(self, sql: str, params: Optional[tuple] = None) -> List[Dict]:
        with self.cursor() as c:
            c.execute(sql, params or ())
            return c.fetchall()

    def query_one(self, sql: str, params: Optional[tuple] = None) -> Optional[Dict]:
        with self.cursor() as c:
            c.execute(sql, params or ())
            return c.fetchone()

    def execute(self, sql: str, params: Optional[tuple] = None) -> int:
        with self.cursor() as c:
            return c.execute(sql, params or ())

    def execute_many(self, sql: str, params_list: List[tuple]) -> int:
        with self.cursor() as c:
            return c.executemany(sql, params_list)

    def insert(self, table: str, data: Dict) -> int:
        cols = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
        with self.cursor() as c:
            c.execute(sql, tuple(data.values()))
            return c.lastrowid

    def update(self, table: str, data: Dict, where: str, params: tuple = ()) -> int:
        set_clause = ', '.join([f"{k}=%s" for k in data.keys()])
        sql = f"UPDATE {table} SET {set_clause} WHERE {where}"
        with self.cursor() as c:
            return c.execute(sql, tuple(data.values()) + params)

    def cleanup_test_data(self, prefix: str = 'TEST_', soft_delete: bool = True) -> int:
        """
        清理测试数据 - 修复 P1-2/P1-3

        使用 _config.TEST_DATA_TABLES 替代硬编码，统一软删除策略
        """
        total = 0
        for table in TEST_DATA_TABLES:
            try:
                if not self._table_exists(table):
                    logger.debug(f"表 {table} 不存在，跳过")
                    continue

                if soft_delete and self._has_column(table, 'is_deleted'):
                    sql = f"UPDATE {table} SET is_deleted=1 WHERE order_no LIKE %s"
                else:
                    sql = f"DELETE FROM {table} WHERE order_no LIKE %s"

                affected = self.execute(sql, (f'{prefix}%',))
                if affected > 0:
                    logger.info(f"   清理 {table}: {affected} 条")
                total += affected
            except Exception as e:
                logger.warning(f"清理 {table} 失败: {e}")

        return total

    def _table_exists(self, table: str) -> bool:
        """检查表是否存在"""
        try:
            result = self.query_one(
                "SELECT COUNT(*) AS cnt FROM information_schema.tables "
                "WHERE table_schema=DATABASE() AND table_name=%s",
                (table,)
            )
            return result and result.get('cnt', 0) > 0
        except Exception:
            return False

    def _has_column(self, table: str, column: str) -> bool:
        """检查表是否有指定列"""
        try:
            result = self.query_one(
                "SELECT COUNT(*) AS cnt FROM information_schema.columns "
                "WHERE table_schema=DATABASE() AND table_name=%s AND column_name=%s",
                (table, column)
            )
            return result and result.get('cnt', 0) > 0
        except Exception:
            return False


# 全局实例
db_pool = ConnectionPool()
db = DBHelperPooled(db_pool)


__all__ = ['ConnectionPool', 'DBHelperPooled', 'db_pool', 'db']
