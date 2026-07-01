# -*- coding: utf-8 -*-
"""
数据库事务上下文管理器

功能说明：
- 提供安全的数据库事务封装
- 自动提交/回滚
- 连接池管理
- 防止连接泄漏

使用方式：
    from db_transaction import with_transaction, get_db_connection

    # 方式1: 装饰器
    @with_transaction
    def my_func(conn):
        cursor = conn.cursor()
        cursor.execute("INSERT INTO ...")
        return True

    # 方式2: 上下文管理器
    with TransactionContext() as tx:
        tx.cursor.execute("INSERT INTO ...")
        tx.cursor.execute("UPDATE ...")
        tx.commit()
"""
import os
import logging
import threading
from contextlib import contextmanager
from typing import Optional, Callable, Any, Tuple

logger = logging.getLogger(__name__)


class TransactionError(Exception):
    """事务异常"""
    pass


class TransactionContext:
    """
    事务上下文管理器

    使用示例：
        with TransactionContext() as tx:
            tx.cursor.execute("INSERT INTO orders VALUES (%s, %s)", (no, name))
            tx.cursor.execute("INSERT INTO items VALUES (%s, %s)", (id, no))
            tx.commit()
    """

    def __init__(self, connection=None, auto_rollback=True):
        self._conn = connection
        self._cursor = None
        self._committed = False
        self._auto_rollback = auto_rollback
        self._owns_connection = False

    def __enter__(self):
        if self._conn is None:
            self._conn = self._get_connection()
            self._owns_connection = True

        self._cursor = self._conn.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._cursor:
            try:
                self._cursor.close()
            except Exception as e:
                logger.warning(f"[Transaction] 游标关闭失败: {e}")

        if self._owns_connection and self._conn:
            if exc_type is not None and self._auto_rollback:
                try:
                    self._conn.rollback()
                    logger.info("[Transaction] 回滚事务")
                except Exception as e:
                    logger.error(f"[Transaction] 回滚失败: {e}")
            elif self._committed:
                try:
                    self._conn.commit()
                except Exception as e:
                    logger.error(f"[Transaction] 提交失败: {e}")
                    try:
                        self._conn.rollback()
                    except Exception as re:
                        logger.warning(f"[Transaction] 提交后回滚失败: {re}")
                    raise TransactionError(f"提交失败: {e}")

            try:
                self._conn.close()
            except Exception as e:
                logger.warning(f"[Transaction] 连接关闭失败: {e}")

        return False

    def _get_connection(self):
        """获取数据库连接"""
        from models.database import get_connection
        return get_connection()

    @property
    def cursor(self):
        """获取游标"""
        return self._cursor

    @property
    def connection(self):
        """获取连接"""
        return self._conn

    def commit(self):
        """标记为已提交"""
        self._committed = True

    def rollback(self):
        """回滚事务"""
        if self._conn:
            self._conn.rollback()
            self._committed = False
            logger.info("[Transaction] 手动回滚事务")


@contextmanager
def with_transaction(connect_func: Optional[Callable[[], Any]] = None):
    """
    事务上下文管理器装饰器/生成器

    参数说明：
        connect_func: 数据库连接获取函数，默认使用 models.database.get_connection

    使用示例：
        def update_order(conn, order_id, data):
            with with_transaction() as tx:
                tx.cursor.execute("UPDATE orders SET ... WHERE id=%s", (order_id,))
                tx.cursor.execute("UPDATE items SET ... WHERE order_id=%s", (order_id,))
                tx.commit()
    """
    conn = None
    cursor = None
    committed = False

    try:
        if connect_func:
            conn = connect_func()
        else:
            from models.database import get_connection
            conn = get_connection()

        cursor = conn.cursor()
        tx = TransactionContext(conn)
        tx._cursor = cursor

        yield tx

        tx.commit()
        committed = True

    except Exception as e:
        logger.error(f"[Transaction] 事务执行异常: {e}")
        if conn:
            try:
                conn.rollback()
                logger.info("[Transaction] 已回滚事务")
            except Exception as rollback_err:
                logger.error(f"[Transaction] 回滚失败: {rollback_err}")
        raise TransactionError(str(e))

    finally:
        if cursor:
            try:
                cursor.close()
            except Exception as e:
                logger.warning(f"[Transaction] 游标关闭失败: {e}")

        if conn:
            try:
                conn.close()
            except Exception as e:
                logger.warning(f"[Transaction] 连接关闭失败: {e}")

        if not committed:
            logger.warning("[Transaction] 事务未提交（可能已回滚）")


def with_retry(max_attempts: int = 3, delay: float = 0.5) -> Callable:
    """
    重试装饰器（用于数据库操作）

    参数说明：
        max_attempts (int): 最大重试次数
        delay (float): 重试间隔（秒）

    使用示例：
        @with_retry(max_attempts=3)
        def flaky_operation():
            # 可能失败的数据库操作
            pass
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            last_error = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_attempts:
                        logger.warning(
                            f"[Retry] {func.__name__} 第{attempt}次失败，"
                            f"{delay}秒后重试: {e}"
                        )
                        import time
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"[Retry] {func.__name__} 重试{max_attempts}次后仍失败: {e}"
                        )

            raise last_error

        return wrapper
    return decorator


class ReadOnlyTransaction:
    """只读事务上下文"""

    def __init__(self, connection=None):
        self._conn = connection
        self._cursor = None

    def __enter__(self):
        if self._conn is None:
            from models.database import get_connection
            self._conn = get_connection()

        self._cursor = self._conn.cursor()
        self._cursor.execute("START TRANSACTION READ ONLY")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._cursor:
            try:
                self._cursor.close()
            except Exception as e:
                logger.warning(f"[ReadOnlyTransaction] 游标关闭失败: {e}")

        if self._conn:
            try:
                self._conn.rollback()
            except Exception as e:
                logger.warning(f"[ReadOnlyTransaction] 回滚失败: {e}")
            try:
                self._conn.close()
            except Exception as e:
                logger.warning(f"[ReadOnlyTransaction] 连接关闭失败: {e}")

        return False

    @property
    def cursor(self):
        return self._cursor

    @property
    def connection(self):
        return self._conn


@contextmanager
def read_only():
    """
    只读事务上下文管理器

    使用示例：
        with read_only() as ro:
            ro.cursor.execute("SELECT * FROM orders WHERE id=%s", (id,))
            result = ro.cursor.fetchone()
    """
    yield ReadOnlyTransaction()
