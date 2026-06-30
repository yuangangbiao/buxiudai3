# -*- coding: utf-8 -*-
"""
订单数据同步脚本
从原数据库(MySQL)同步订单数据到目标数据库(SQLite)
"""

import os
import sys
from pathlib import Path
from typing import List, Dict
from datetime import datetime

# 路径配置
SOURCE_DIR = r"d:\yuan\不锈钢网带跟单3.0"
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from core.logger import get_logger
from core.db import db
from core.config import ensure_dir, get_sqlite_path, is_sqlite
from services.order_service import OrderService

logger = get_logger(__name__)


class OrderSync:
    """订单数据同步"""

    def __init__(self):
        self.source_dir = SOURCE_DIR
        self._mysql_conn = None

    def _get_source_mysql_connection(self):
        """获取源数据库MySQL连接"""
        if self._mysql_conn is None:
            try:
                import pymysql
                self._mysql_conn = pymysql.connect(
                    host='localhost',
                    port=3306,
                    user='root',
                    password=os.getenv('MYSQL_PASSWORD'),
                    database='steel_belt',
                    charset='utf8mb4',
                    cursorclass=pymysql.cursors.DictCursor
                )
                logger.info("源数据库MySQL连接成功")
            except Exception as e:
                logger.error(f"源数据库MySQL连接失败: {e}")
                raise
        return self._mysql_conn

    def create_tables(self):
        """创建订单相关表"""
        orders_sql = """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_no TEXT UNIQUE NOT NULL,
            customer_name TEXT NOT NULL,
            customer_phone TEXT,
            customer_address TEXT,
            customer_group TEXT,
            product_type TEXT NOT NULL,
            material TEXT DEFAULT '',
            mesh_size REAL,
            wire_diameter REAL,
            width REAL,
            length REAL,
            quantity INTEGER DEFAULT 1,
            unit TEXT DEFAULT '米',
            unit_price REAL DEFAULT 0,
            total_amount REAL DEFAULT 0,
            surface_treatment TEXT,
            special_requirements TEXT,
            delivery_date TEXT,
            status TEXT DEFAULT '待确认',
            remark TEXT,
            extra_params TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """

        production_orders_sql = """
        CREATE TABLE IF NOT EXISTS production_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_order_no TEXT UNIQUE NOT NULL,
            order_id INTEGER NOT NULL,
            priority INTEGER DEFAULT 5,
            plan_start TEXT,
            plan_end TEXT,
            actual_start TEXT,
            actual_end TEXT,
            assigned_to TEXT,
            status TEXT DEFAULT '待开始',
            remark TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )
        """

        try:
            with db.get_cursor() as cursor:
                cursor.execute(orders_sql)
                cursor.execute(production_orders_sql)

                # 创建索引
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_order_no ON orders(order_no)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_name)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_prod_orders_work_no ON production_orders(work_order_no)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_prod_orders_order_id ON production_orders(order_id)")

            logger.info("订单表和工单表已创建")
        except Exception as e:
            logger.error(f"创建订单表失败: {e}")
            raise

    def load_source_orders(self) -> List[Dict]:
        """从源数据库(MySQL)加载订单数据"""
        try:
            conn = self._get_source_mysql_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM orders
                WHERE status NOT IN ('已完成', '已取消', '已归档', 'completed', 'cancelled', 'archived')
                ORDER BY updated_at DESC
            """)
            rows = cursor.fetchall()
            orders = list(rows) if rows else []

            cursor.close()

            logger.info(f"从源数据库加载了 {len(orders)} 条订单")
            return orders

        except Exception as e:
            logger.error(f"加载源订单失败: {e}")
            return []

    def close(self):
        """关闭连接"""
        if self._mysql_conn:
            self._mysql_conn.close()
            self._mysql_conn = None

    def sync_orders(self) -> Dict[str, int]:
        """同步订单到目标数据库"""
        stats = {
            'total': 0,
            'inserted': 0,
            'skipped': 0,
            'errors': 0
        }

        orders = self.load_source_orders()
        stats['total'] = len(orders)

        for order in orders:
            try:
                order_no = order.get('order_no', '')
                if not order_no:
                    stats['skipped'] += 1
                    continue

                # 检查是否已存在
                existing = OrderService.get_order_by_id(order.get('id'))
                if existing:
                    stats['skipped'] += 1
                    continue

                # 插入订单
                with db.get_cursor() as cursor:
                    fields = [
                        'id', 'order_no', 'customer_name', 'customer_phone',
                        'customer_address', 'customer_group', 'product_type',
                        'material', 'mesh_size', 'wire_diameter', 'width',
                        'length', 'quantity', 'unit', 'unit_price',
                        'total_amount', 'surface_treatment',
                        'special_requirements', 'delivery_date', 'status',
                        'remark', 'extra_params', 'created_at', 'updated_at'
                    ]

                    placeholders = ', '.join(['?' for _ in fields])
                    columns = ', '.join(fields)
                    sql = f"INSERT INTO orders ({columns}) VALUES ({placeholders})"

                    # 转换Decimal类型为float
                    def convert_value(v):
                        if v is None:
                            return None
                        if hasattr(v, '__float__'):
                            return float(v)
                        return v

                    values = tuple(convert_value(order.get(f)) for f in fields)
                    cursor.execute(sql, values)

                stats['inserted'] += 1

            except Exception as e:
                logger.error(f"同步订单失败 {order.get('order_no')}: {e}")
                stats['errors'] += 1

        return stats


def main():
    """主函数"""
    print("=" * 60)
    print("订单数据同步工具")
    print("=" * 60)
    print()

    # 确保目录存在
    db_path = get_sqlite_path()
    ensure_dir(os.path.dirname(db_path))

    sync = OrderSync()

    try:
        # 创建表
        print("[1/3] 创建订单表...")
        sync.create_tables()
        print("      完成")
        print()

        # 同步订单
        print("[2/3] 同步订单数据...")
        stats = sync.sync_orders()
        print(f"      总数: {stats['total']}")
        print(f"      新增: {stats['inserted']}")
        print(f"      跳过: {stats['skipped']}")
        print(f"      错误: {stats['errors']}")
        print()

        # 验证
        print("[3/3] 验证结果...")
        count = OrderService.get_order_count()
        print(f"      目标数据库现有 {count} 条订单")
        print()

        print("=" * 60)
        print("同步完成！")
        print("=" * 60)
    finally:
        sync.close()


if __name__ == "__main__":
    main()
