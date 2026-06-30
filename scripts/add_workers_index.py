# -*- coding: utf-8 -*-
"""
为 workers 表添加索引，加速慢查询

慢查询:
  SELECT enterprise_id, name, role, department, status FROM workers WHERE status=%s ORDER BY name
  耗时: 2091ms

原因:
  1. workers 表没有 (status, name) 复合索引
  2. 需要全表扫描 + filesort

解决方案:
  添加索引: CREATE INDEX idx_workers_status_name ON workers(status, name)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
import pymysql


def add_workers_index():
    conn = pymysql.connect(
        **CONTAINER_MYSQL_CFG,
        connect_timeout=DB_CONNECT_TIMEOUT
    )
    cursor = conn.cursor()

    try:
        cursor.execute("SHOW INDEX FROM workers")
        existing_indexes = cursor.fetchall()
        print("现有索引:")
        for idx in existing_indexes:
            print(f"  {idx}")

        cursor.execute("SELECT COUNT(*) FROM workers")
        count = cursor.fetchone()[0]
        print(f"\nworkers 表记录数: {count}")

        index_exists = any(
            idx[2] == 'idx_workers_status_name'
            for idx in existing_indexes
        )

        if index_exists:
            print("\n索引 idx_workers_status_name 已存在，无需添加")
            return

        print("\n添加索引 idx_workers_status_name ...")
        cursor.execute("""
            CREATE INDEX idx_workers_status_name ON workers(status, name)
        """)
        conn.commit()
        print("索引添加成功！")

        cursor.execute("SHOW INDEX FROM workers")
        new_indexes = cursor.fetchall()
        print("\n新索引列表:")
        for idx in new_indexes:
            print(f"  {idx}")

    except pymysql.Error as e:
        print(f"错误: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    add_workers_index()
