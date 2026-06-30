# -*- coding: utf-8 -*-
"""
订单数据同步和归档功能脚本
将订单数据同步到目标数据库，并支持归档功能
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# 路径配置
SOURCE_DIR = r"d:\yuan\不锈钢网带跟单3.0"
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from core.logger import get_logger
from core.db import db
from core.config import ensure_dir, get_sqlite_path, is_sqlite

logger = get_logger(__name__)


class OrderArchiveManager:
    """订单归档管理器"""

    def __init__(self):
        self.archive_table_name = "order_archive"

    def create_archive_table(self):
        """创建归档表（不影响原表）"""
        if is_sqlite():
            create_sql = """
            CREATE TABLE IF NOT EXISTS order_archive (
                id INTEGER PRIMARY KEY,
                order_no TEXT NOT NULL,
                customer_name TEXT,
                customer_phone TEXT,
                customer_address TEXT,
                customer_group TEXT,
                product_type TEXT,
                material TEXT,
                mesh_size REAL,
                wire_diameter REAL,
                width REAL,
                length REAL,
                quantity INTEGER,
                unit TEXT,
                unit_price REAL,
                total_amount REAL,
                surface_treatment TEXT,
                special_requirements TEXT,
                delivery_date TEXT,
                status TEXT,
                remark TEXT,
                extra_params TEXT,
                created_at TEXT,
                updated_at TEXT,
                original_table TEXT DEFAULT 'orders',
                archived_at TEXT DEFAULT CURRENT_TIMESTAMP,
                archive_reason TEXT,
                archived_by TEXT
            )
            """
            # 创建索引
            index_sqls = [
                "CREATE INDEX IF NOT EXISTS idx_archive_order_no ON order_archive(order_no)",
                "CREATE INDEX IF NOT EXISTS idx_archive_customer ON order_archive(customer_name)",
                "CREATE INDEX IF NOT EXISTS idx_archive_archived_at ON order_archive(archived_at)",
                "CREATE INDEX IF NOT EXISTS idx_archive_status ON order_archive(status)",
            ]
        else:
            create_sql = """
            CREATE TABLE IF NOT EXISTS order_archive (
                id INT PRIMARY KEY,
                order_no VARCHAR(50) NOT NULL,
                customer_name VARCHAR(100),
                customer_phone VARCHAR(20),
                customer_address VARCHAR(255),
                customer_group VARCHAR(50),
                product_type VARCHAR(50),
                material VARCHAR(50),
                mesh_size DECIMAL(10,2),
                wire_diameter DECIMAL(10,2),
                width DECIMAL(10,2),
                length DECIMAL(10,2),
                quantity INT,
                unit VARCHAR(10),
                unit_price DECIMAL(10,2),
                total_amount DECIMAL(10,2),
                surface_treatment VARCHAR(50),
                special_requirements TEXT,
                delivery_date DATETIME,
                status VARCHAR(20),
                remark TEXT,
                extra_params TEXT,
                created_at DATETIME,
                updated_at DATETIME,
                original_table VARCHAR(20) DEFAULT 'orders',
                archived_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                archive_reason VARCHAR(50),
                archived_by VARCHAR(50)
            )
            """
            index_sqls = [
                "CREATE INDEX idx_archive_order_no ON order_archive(order_no)",
                "CREATE INDEX idx_archive_customer ON order_archive(customer_name)",
                "CREATE INDEX idx_archive_archived_at ON order_archive(archived_at)",
                "CREATE INDEX idx_archive_status ON order_archive(status)",
            ]

        try:
            with db.get_cursor() as cursor:
                cursor.execute(create_sql)
                for idx_sql in index_sqls:
                    cursor.execute(idx_sql)
            logger.info(f"归档表 {self.archive_table_name} 已创建/存在")
        except Exception as e:
            logger.error(f"创建归档表失败: {e}")
            raise

    def can_delete(self, order_id: int) -> Tuple[bool, str]:
        """
        检查订单是否可以删除

        Returns:
            (can_delete, reason)
        """
        try:
            with db.get_cursor(commit=False) as cursor:
                if is_sqlite():
                    cursor.execute(
                        "SELECT id, status FROM orders WHERE id = ?",
                        (order_id,)
                    )
                else:
                    cursor.execute(
                        "SELECT id, status FROM orders WHERE id = %s",
                        (order_id,)
                    )
                order = cursor.fetchone()

            if not order:
                return False, "订单不存在"

            status = order.get('status') if isinstance(order, dict) else order[1]

            # 已完成、已发货、已取消的订单不能删除
            if status in ['已完成', '已发货', 'completed', 'shipped']:
                return False, f"订单状态为'{status}'，不能删除"

            # 检查是否有生产计划
            with db.get_cursor(commit=False) as cursor:
                if is_sqlite():
                    cursor.execute(
                        "SELECT COUNT(*) as cnt FROM production_orders WHERE order_id = ?",
                        (order_id,)
                    )
                else:
                    cursor.execute(
                        "SELECT COUNT(*) as cnt FROM production_orders WHERE order_id = %s",
                        (order_id,)
                    )
                result = cursor.fetchone()
                prod_count = result.get('cnt') if isinstance(result, dict) else result[0]

            if prod_count > 0:
                return False, f"订单存在{prod_count}个生产工单，不能删除"

            return True, "可以删除"

        except Exception as e:
            logger.error(f"检查删除权限失败: {e}")
            return False, f"检查失败: {e}"

    def can_archive(self, order_id: int) -> Tuple[bool, str]:
        """
        检查订单是否可以归档

        Returns:
            (can_archive, reason)
        """
        try:
            with db.get_cursor(commit=False) as cursor:
                if is_sqlite():
                    cursor.execute(
                        "SELECT id, status FROM orders WHERE id = ?",
                        (order_id,)
                    )
                else:
                    cursor.execute(
                        "SELECT id, status FROM orders WHERE id = %s",
                        (order_id,)
                    )
                order = cursor.fetchone()

            if not order:
                return False, "订单不存在"

            status = order.get('status') if isinstance(order, dict) else order[1]

            # 只有已完成或已取消的订单才能归档
            if status in ['已完成', '已取消', 'completed', 'cancelled']:
                return True, "可以归档"

            return False, f"订单状态为'{status}'，只有已完成或已取消的订单才能归档"

        except Exception as e:
            logger.error(f"检查归档权限失败: {e}")
            return False, f"检查失败: {e}"

    def delete_order(self, order_id: int, operator: str = "系统") -> Tuple[bool, str]:
        """
        删除未排产的订单

        Args:
            order_id: 订单ID
            operator: 操作人

        Returns:
            (success, message)
        """
        can_delete, reason = self.can_delete(order_id)
        if not can_delete:
            return False, reason

        try:
            with db.get_cursor() as cursor:
                # 获取订单信息用于日志
                if is_sqlite():
                    cursor.execute("SELECT order_no FROM orders WHERE id = ?", (order_id,))
                else:
                    cursor.execute("SELECT order_no FROM orders WHERE id = %s", (order_id,))
                order = cursor.fetchone()
                order_no = order.get('order_no') if order else 'unknown'

                # 删除订单
                if is_sqlite():
                    cursor.execute("DELETE FROM orders WHERE id = ?", (order_id,))
                else:
                    cursor.execute("DELETE FROM orders WHERE id = %s", (order_id,))

            logger.info(f"订单已删除: id={order_id}, order_no={order_no}, operator={operator}")
            return True, f"订单 {order_no} 已删除"

        except Exception as e:
            logger.error(f"删除订单失败: {e}")
            return False, f"删除失败: {e}"

    def archive_order(self, order_id: int, reason: str = "manual",
                     operator: str = "系统") -> Tuple[bool, str]:
        """
        归档已完成的订单

        Args:
            order_id: 订单ID
            reason: 归档原因
            operator: 操作人

        Returns:
            (success, message)
        """
        can_archive, check_reason = self.can_archive(order_id)
        if not can_archive:
            return False, check_reason

        try:
            with db.get_cursor() as cursor:
                # 获取订单完整信息
                if is_sqlite():
                    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
                else:
                    cursor.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
                order = cursor.fetchone()

                if not order:
                    return False, "订单不存在"

                # 构建归档数据
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                if isinstance(order, dict):
                    archive_data = {
                        'id': order['id'],
                        'order_no': order.get('order_no', ''),
                        'customer_name': order.get('customer_name', ''),
                        'customer_phone': order.get('customer_phone', ''),
                        'customer_address': order.get('customer_address', ''),
                        'customer_group': order.get('customer_group', ''),
                        'product_type': order.get('product_type', ''),
                        'material': order.get('material', ''),
                        'mesh_size': order.get('mesh_size'),
                        'wire_diameter': order.get('wire_diameter'),
                        'width': order.get('width'),
                        'length': order.get('length'),
                        'quantity': order.get('quantity'),
                        'unit': order.get('unit', ''),
                        'unit_price': order.get('unit_price'),
                        'total_amount': order.get('total_amount'),
                        'surface_treatment': order.get('surface_treatment', ''),
                        'special_requirements': order.get('special_requirements', ''),
                        'delivery_date': str(order.get('delivery_date')) if order.get('delivery_date') else None,
                        'status': order.get('status', ''),
                        'remark': order.get('remark', ''),
                        'extra_params': order.get('extra_params', ''),
                        'created_at': str(order.get('created_at')) if order.get('created_at') else None,
                        'updated_at': str(order.get('updated_at')) if order.get('updated_at') else None,
                        'original_table': 'orders',
                        'archived_at': now,
                        'archive_reason': reason,
                        'archived_by': operator,
                    }
                else:
                    # tuple result
                    archive_data = {
                        'id': order[0],
                        'order_no': order[1],
                        'customer_name': order[2],
                        'customer_phone': order[3] if len(order) > 3 else '',
                        'status': order[18] if len(order) > 18 else '',
                        'original_table': 'orders',
                        'archived_at': now,
                        'archive_reason': reason,
                        'archived_by': operator,
                    }

                # 插入归档表
                if is_sqlite():
                    placeholders = ', '.join(['?' for _ in archive_data])
                    columns = ', '.join(archive_data.keys())
                    sql = f"INSERT INTO {self.archive_table_name} ({columns}) VALUES ({placeholders})"
                else:
                    columns = ', '.join(archive_data.keys())
                    placeholders = ', '.join(['%s' for _ in archive_data])
                    sql = f"INSERT INTO {self.archive_table_name} ({columns}) VALUES ({placeholders})"

                cursor.execute(sql, tuple(archive_data.values()))

                # 从原表删除（可选，也可以标记为已归档）
                if is_sqlite():
                    cursor.execute("DELETE FROM orders WHERE id = ?", (order_id,))
                else:
                    cursor.execute("DELETE FROM orders WHERE id = %s", (order_id,))

            logger.info(f"订单已归档: id={order_id}, order_no={archive_data.get('order_no')}, reason={reason}")
            return True, f"订单 {archive_data.get('order_no')} 已归档"

        except Exception as e:
            logger.error(f"归档订单失败: {e}")
            return False, f"归档失败: {e}"

    def restore_order(self, archive_id: int, operator: str = "系统") -> Tuple[bool, str]:
        """
        从归档恢复订单

        Args:
            archive_id: 归档表中的ID
            operator: 操作人

        Returns:
            (success, message)
        """
        try:
            with db.get_cursor() as cursor:
                # 从归档表获取数据
                if is_sqlite():
                    cursor.execute("SELECT * FROM order_archive WHERE id = ?", (archive_id,))
                else:
                    cursor.execute("SELECT * FROM order_archive WHERE id = %s", (archive_id,))
                archive = cursor.fetchone()

                if not archive:
                    return False, "归档记录不存在"

                if isinstance(archive, dict):
                    order_data = {
                        'order_no': archive.get('order_no', ''),
                        'customer_name': archive.get('customer_name', ''),
                        'customer_phone': archive.get('customer_phone', ''),
                        'customer_address': archive.get('customer_address', ''),
                        'customer_group': archive.get('customer_group', ''),
                        'product_type': archive.get('product_type', ''),
                        'material': archive.get('material', ''),
                        'mesh_size': archive.get('mesh_size'),
                        'wire_diameter': archive.get('wire_diameter'),
                        'width': archive.get('width'),
                        'length': archive.get('length'),
                        'quantity': archive.get('quantity'),
                        'unit': archive.get('unit', '米'),
                        'unit_price': archive.get('unit_price'),
                        'total_amount': archive.get('total_amount'),
                        'surface_treatment': archive.get('surface_treatment', ''),
                        'special_requirements': archive.get('special_requirements', ''),
                        'delivery_date': archive.get('delivery_date'),
                        'status': '已完成' if archive.get('status') in ['已完成', 'completed'] else '已取消',
                        'remark': archive.get('remark', ''),
                        'extra_params': archive.get('extra_params', ''),
                    }
                else:
                    return False, "数据格式错误"

                # 插入回原表
                columns = ', '.join(order_data.keys())
                if is_sqlite():
                    placeholders = ', '.join(['?' for _ in order_data])
                else:
                    placeholders = ', '.join(['%s' for _ in order_data])

                sql = f"INSERT INTO orders ({columns}) VALUES ({placeholders})"
                cursor.execute(sql, tuple(order_data.values()))

                # 从归档表删除
                if is_sqlite():
                    cursor.execute("DELETE FROM order_archive WHERE id = ?", (archive_id,))
                else:
                    cursor.execute("DELETE FROM order_archive WHERE id = %s", (archive_id,))

            logger.info(f"订单已恢复: archive_id={archive_id}, operator={operator}")
            return True, f"订单已恢复"

        except Exception as e:
            logger.error(f"恢复订单失败: {e}")
            return False, f"恢复失败: {e}"

    def get_archive_list(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """获取归档列表"""
        try:
            with db.get_cursor(commit=False) as cursor:
                if is_sqlite():
                    cursor.execute(
                        "SELECT id, order_no, customer_name, product_type, status, archived_at, archive_reason "
                        "FROM order_archive ORDER BY archived_at DESC LIMIT ? OFFSET ?",
                        (limit, offset)
                    )
                else:
                    cursor.execute(
                        "SELECT id, order_no, customer_name, product_type, status, archived_at, archive_reason "
                        "FROM order_archive ORDER BY archived_at DESC LIMIT %s OFFSET %s",
                        (limit, offset)
                    )
                results = cursor.fetchall()
                return [dict(row) for row in results] if results else []
        except Exception as e:
            logger.error(f"获取归档列表失败: {e}")
            return []

    def get_archive_count(self) -> int:
        """获取归档数量"""
        try:
            with db.get_cursor(commit=False) as cursor:
                cursor.execute("SELECT COUNT(*) as cnt FROM order_archive")
                result = cursor.fetchone()
                return result.get('cnt') if isinstance(result, dict) else result[0]
        except Exception as e:
            logger.error(f"获取归档数量失败: {e}")
            return 0


def main():
    """主函数"""
    print("=" * 60)
    print("订单归档功能初始化工具")
    print("=" * 60)
    print()

    # 确保目录存在
    db_path = get_sqlite_path()
    ensure_dir(os.path.dirname(db_path))

    manager = OrderArchiveManager()

    # 创建归档表
    print("[1/2] 创建归档表...")
    manager.create_archive_table()
    print("      完成")
    print()

    # 验证
    print("[2/2] 验证归档表...")
    count = manager.get_archive_count()
    print(f"      归档表已创建，当前有 {count} 条归档记录")
    print()

    print("=" * 60)
    print("初始化完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
