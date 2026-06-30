# -*- coding: utf-8 -*-
"""
Service 统一模板

提供所有 Service 类的基类，封装事务管理和 DAO 注入等通用能力。
所有业务 Service 应继承 BaseService 以获得统一的事务支持。
"""

import logging
from contextlib import contextmanager
from typing import Optional, Any

from models.database import get_connection

logger = logging.getLogger(__name__)


class BaseService:
    """Service 基类

    提供：
    - DAO 依赖注入
    - transaction() 事务上下文管理器

    用法::

        class MyService(BaseService):
            def do_something(self):
                with self.transaction() as conn:
                    cursor = conn.cursor()
                    cursor.execute(...)
                    conn.commit()  # 由上下文管理器自动提交
    """

    def __init__(self, dao: Optional[Any] = None):
        """初始化 Service 实例。

        Args:
            dao: 数据访问对象（DAO），可选。子类可在构造时注入自定义 DAO，
                 若不提供则由子类自行设置默认值。
        """
        self.dao = dao

    @contextmanager
    def transaction(self):
        """事务上下文管理器

        自动管理数据库连接的获取、提交、回滚和归还。

        - 正常退出时自动 commit
        - 异常时自动 rollback
        - 无论成功或失败，finally 中归还连接到连接池

        Yields:
            数据库连接对象（PooledConnection），可直接用于执行 SQL。

        Raises:
            原样抛出上下文内发生的任何异常，不吞没。

        用法::

            with self.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE orders SET status=%s WHERE id=%s", (new_status, order_id))
        """
        conn = get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            logger.exception(
                "[BaseService] 事务回滚",
                extra={"dao": type(self.dao).__name__ if self.dao else "None"}
            )
            raise
        finally:
            conn.close()
