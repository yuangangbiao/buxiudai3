# -*- coding: utf-8 -*-
"""
测试数据清理器

修复 P1-2 + P1-3: 提供统一的测试数据清理逻辑，使用 _config.TEST_DATA_TABLES 避免硬编码
"""
import logging
from typing import List, Optional

from tests.core._config import TEST_DATA_TABLES
from tests.core.db_pool import db

logger = logging.getLogger(__name__)


def cleanup_test_data(
    prefix: Optional[str] = None,
    tables: Optional[List[str]] = None,
    hard_delete: bool = False,
) -> int:
    """
    清理测试数据

    Args:
        prefix: 订单号/标识前缀（仅清理匹配前缀的数据）
        tables: 要清理的表（None 使用 _config.TEST_DATA_TABLES）
        hard_delete: True 物理删除，False 软删除（is_deleted=1）

    Returns:
        total: 总清理条数
    """
    tables = tables or TEST_DATA_TABLES
    total = 0

    for table in tables:
        if not _table_exists(table):
            logger.debug(f"表 {table} 不存在，跳过")
            continue

        try:
            affected = _cleanup_table(table, prefix, hard_delete)
            total += affected
            if affected > 0:
                logger.info(f"  清理表 {table}: {affected} 条")
        except Exception as e:
            logger.warning(f"清理表 {table} 失败: {e}")

    logger.info(f"总清理: {total} 条")
    return total


def _table_exists(table: str) -> bool:
    """检查表是否存在"""
    try:
        result = db.query_one(
            "SELECT COUNT(*) AS cnt FROM information_schema.tables "
            "WHERE table_schema=DATABASE() AND table_name=%s",
            (table,)
        )
        return result and result.get('cnt', 0) > 0
    except Exception:
        return False


def _cleanup_table(table: str, prefix: Optional[str], hard_delete: bool) -> int:
    """清理单表"""
    if hard_delete:
        if prefix:
            sql = f"DELETE FROM {table} WHERE order_no LIKE %s"
            return db.execute(sql, (f"{prefix}%",))
        else:
            sql = f"DELETE FROM {table} WHERE is_test=1 OR order_no LIKE 'TEST_%'"
            return db.execute(sql)
    else:
        # 软删除
        if prefix:
            sql = f"UPDATE {table} SET is_deleted=1 WHERE order_no LIKE %s"
            return db.execute(sql, (f"{prefix}%",))
        else:
            sql = f"UPDATE {table} SET is_deleted=1 WHERE is_test=1 OR order_no LIKE 'TEST_%'"
            return db.execute(sql)


def cleanup_by_prefix(prefix: str, hard_delete: bool = False) -> int:
    """按 prefix 清理（最常用）"""
    return cleanup_test_data(prefix=prefix, hard_delete=hard_delete)


def cleanup_all_test_data(hard_delete: bool = False) -> int:
    """清理所有测试数据（谨慎使用）"""
    return cleanup_test_data(prefix=None, hard_delete=hard_delete)


__all__ = [
    'cleanup_test_data',
    'cleanup_by_prefix',
    'cleanup_all_test_data',
]
