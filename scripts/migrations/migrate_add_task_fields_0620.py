# -*- coding: utf-8 -*-
"""
T0: DDL 迁移脚本 - 添加任务表字段

执行时间: 2026-06-20
执行顺序: T0 (第一个执行)

DDL:
1. process_sub_steps 添加 completed_qty 字段
2. data_packages 添加 is_archived 标记字段

回滚:
ALTER TABLE process_sub_steps DROP COLUMN completed_qty;
ALTER TABLE data_packages DROP COLUMN is_archived;
"""
import os
import sys

PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJ_ROOT not in sys.path:
    sys.path.insert(0, PROJ_ROOT)

from mobile_api_ai.storage.mysql_storage import MySQLStorage


def migrate():
    """执行 DDL 迁移"""
    storage = MySQLStorage()

    print("[T0.1] 检查 process_sub_steps.completed_qty 字段...")
    result = storage.fetch_one("""
        SELECT COLUMN_NAME FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'process_sub_steps'
          AND COLUMN_NAME = 'completed_qty'
    """)
    if result:
        print("[T0.1] completed_qty 字段已存在，跳过")
    else:
        print("[T0.1] 添加 completed_qty 字段...")
        storage.execute("""
            ALTER TABLE process_sub_steps
            ADD COLUMN completed_qty DECIMAL(10,2) DEFAULT 0 AFTER quantity
        """)
        print("[T0.1] ✅ completed_qty 字段添加成功")

    print("[T0.2] 检查 data_packages.is_archived 字段...")
    result = storage.fetch_one("""
        SELECT COLUMN_NAME FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'data_packages'
          AND COLUMN_NAME = 'is_archived'
    """)
    if result:
        print("[T0.2] is_archived 字段已存在，跳过")
    else:
        print("[T0.2] 添加 is_archived 字段...")
        storage.execute("""
            ALTER TABLE data_packages
            ADD COLUMN is_archived TINYINT DEFAULT 0 AFTER flow_type
        """)
        print("[T0.2] ✅ is_archived 字段添加成功")

    print("[T0] ✅ DDL 迁移完成")


def rollback():
    """回滚 DDL"""
    storage = MySQLStorage()

    print("[T0 回滚] 删除 process_sub_steps.completed_qty 字段...")
    try:
        storage.execute("ALTER TABLE process_sub_steps DROP COLUMN completed_qty")
        print("[T0 回滚] ✅ completed_qty 字段已删除")
    except Exception as e:
        print(f"[T0 回滚] ⚠️ completed_qty 删除失败: {e}")

    print("[T0 回滚] 删除 data_packages.is_archived 字段...")
    try:
        storage.execute("ALTER TABLE data_packages DROP COLUMN is_archived")
        print("[T0 回滚] ✅ is_archived 字段已删除")
    except Exception as e:
        print(f"[T0 回滚] ⚠️ is_archived 删除失败: {e}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--rollback', action='store_true', help='回滚 DDL')
    args = parser.parse_args()

    if args.rollback:
        rollback()
    else:
        migrate()
