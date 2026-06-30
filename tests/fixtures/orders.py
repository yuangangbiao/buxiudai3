# -*- coding: utf-8 -*-
"""
订单测试数据工厂

修复 P0-2 + P0-4: 为 parallel.py 提供 make_test_order / cleanup_test_orders
"""
import time
import uuid
import logging
from typing import Optional, Dict, List

from tests.core import db_pool
from tests.core._config import TEST_DATA_TABLES

logger = logging.getLogger(__name__)


def make_test_order(
    product_type: str = '不锈钢网带',
    spec: str = '1.0×10×1000mm',
    quantity: int = 100,
    prefix: str = 'TEST',
    **kwargs
) -> str:
    """
    创建测试订单（自动带 prefix 隔离）

    Returns:
        order_no: 订单号
    """
    order_no = f"{prefix}_{int(time.time())}_{uuid.uuid4().hex[:6].upper()}"

    sql = """
        INSERT INTO orders (
            order_no, product_type, spec, quantity, status,
            customer_name, is_test, create_time
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
    """
    # [v3.7.0 修复] 用 db_pool.db 而非 from-import，便于 mock
    db_pool.db.execute(sql, (
        order_no,
        product_type,
        spec,
        quantity,
        kwargs.get('status', 'PENDING'),
        kwargs.get('customer_name', '测试客户'),
        1,  # is_test=1 标记为测试数据
    ))

    logger.debug(f"创建测试订单: {order_no}")
    return order_no


def make_test_orders(count: int = 5, **kwargs) -> List[str]:
    """批量创建测试订单"""
    return [make_test_order(**kwargs) for _ in range(count)]


def cleanup_test_orders(order_nos: Optional[List[str]] = None, prefix: Optional[str] = None) -> int:
    """
    清理测试订单（软删除）

    Args:
        order_nos: 指定订单号列表（None 则按 prefix 清理）
        prefix: 订单号前缀

    Returns:
        affected: 删除数量
    """
    if order_nos:
        placeholders = ','.join(['%s'] * len(order_nos))
        sql = f"UPDATE orders SET is_deleted=1 WHERE order_no IN ({placeholders})"
        return db_pool.db.execute(sql, tuple(order_nos))

    if prefix:
        # 软删除所有 prefix 开头的订单
        sql = f"UPDATE orders SET is_deleted=1 WHERE order_no LIKE %s"
        return db_pool.db.execute(sql, (f"{prefix}%",))

    return 0


def get_test_order(order_no: str) -> Optional[Dict]:
    """获取测试订单"""
    sql = "SELECT * FROM orders WHERE order_no=%s AND is_deleted=0"
    return db_pool.db.query_one(sql, (order_no,))


__all__ = [
    'make_test_order',
    'make_test_orders',
    'cleanup_test_orders',
    'get_test_order',
]
