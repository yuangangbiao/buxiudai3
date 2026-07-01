# -*- coding: utf-8 -*-
"""
集成测试: 启动前关键表校验

验证 steel_belt 和 container_center 的关键表及必填列存在。
"""
import os

import pymysql
import pytest
from dotenv import load_dotenv

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
load_dotenv(os.path.join(_ROOT, '.env'), override=True)


MYSQL_CFG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', ''),
    'charset': 'utf8mb4',
    'connect_timeout': 5,
}

STEEL_BELT = os.getenv('MYSQL_DATABASE', 'steel_belt')
CONTAINER_CENTER = os.getenv('CONTAINER_MYSQL_DATABASE', 'container_center')

REQUIRED_TABLES = [
    # (数据库, 表名, 必填列)
    (STEEL_BELT,      'sync_queue',            ['id', 'order_no', 'step_name', 'status']),
    (STEEL_BELT,      'production_orders',    ['id', 'order_no', 'status']),
    (STEEL_BELT,      'process_records',      ['id', 'process_code', 'status']),
    (STEEL_BELT,      'process_sub_steps',    ['id', 'order_no', 'step_name']),
    (CONTAINER_CENTER, 'data_packages',        ['id', 'order_no', 'data_type', 'related_order']),
    (CONTAINER_CENTER, 'process_records',      ['id', 'order_no', 'status']),
]


def _conn(database):
    return pymysql.connect(database=database, **MYSQL_CFG)


class TestStartupTables:
    """启动前关键表校验"""

    @pytest.mark.parametrize('database,table,required_cols', REQUIRED_TABLES,
                             ids=[f'{db}.{tbl}' for db, tbl, _ in REQUIRED_TABLES])
    def test_table_exists(self, database, table, required_cols):
        """关键表存在"""
        conn = _conn(database)
        try:
            with conn.cursor() as c:
                c.execute(f"SHOW TABLES LIKE '{table}'")
                result = c.fetchone()
                assert result is not None, (
                    f'{database}.{table} 不存在'
                )
        finally:
            conn.close()

    @pytest.mark.parametrize('database,table,required_cols', REQUIRED_TABLES,
                             ids=[f'{db}.{tbl}' for db, tbl, _ in REQUIRED_TABLES])
    def test_required_columns_exist(self, database, table, required_cols):
        """关键表包含必填列"""
        conn = _conn(database)
        try:
            with conn.cursor() as c:
                c.execute(f"DESCRIBE `{table}`")
                existing = {r[0] for r in c.fetchall()}
                missing = [col for col in required_cols if col not in existing]
                assert not missing, (
                    f'{database}.{table} 缺列: {missing}'
                )
        finally:
            conn.close()
