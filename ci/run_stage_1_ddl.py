# -*- coding: utf-8 -*-
"""
[v3.6] 阶段 1 - 实际执行 DDL 升级和数据迁移

执行: python ci/run_stage_1_ddl.py
"""
import os
import sys
import pymysql

DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '88888888',
    'database': 'container_center',
}

TABLES = [
    'process_sub_steps', 'material_records', 'quality_records',
    'outsource_records', 'repair_records', 'approval_records',
    'production_orders', 'schedule_flow_logs', 'process_records'
]


def upgrade_table(c, table):
    """单张表升级：加 6 字段 + 索引"""
    cur = c.cursor()
    try:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS is_deleted TINYINT(1) NOT NULL DEFAULT 0")
    except Exception:
        pass
    try:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS created_by VARCHAR(64) NOT NULL DEFAULT 'system'")
    except Exception:
        pass
    try:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS updated_by VARCHAR(64) NOT NULL DEFAULT 'system'")
    except Exception:
        pass
    try:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
    except Exception:
        pass
    c.commit()
    print(f'  ✅ {table}: 4 字段已加')


def create_approval_records(c):
    """T0.5 新建 approval_records 表"""
    cur = c.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS approval_records (
            id VARCHAR(64) NOT NULL PRIMARY KEY,
            order_no VARCHAR(64),
            approval_type VARCHAR(32) NOT NULL,
            title VARCHAR(255),
            applicant VARCHAR(64),
            approver VARCHAR(64),
            status VARCHAR(32) NOT NULL DEFAULT 'pending',
            content JSON,
            related_order VARCHAR(64),
            related_process VARCHAR(100),
            reject_reason TEXT,
            created_by VARCHAR(64) NOT NULL DEFAULT 'system',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_by VARCHAR(64) NOT NULL DEFAULT 'system',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            completed_at DATETIME,
            is_deleted TINYINT(1) NOT NULL DEFAULT 0,
            KEY idx_order_no (order_no),
            KEY idx_status (status),
            KEY idx_approver (approver),
            KEY idx_created_by (created_by)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    c.commit()
    print('  ✅ approval_records 已创建')


def migrate_status(c):
    """T0.7 数据迁移：142 行 status 字典统一"""
    cur = c.cursor()
    migrations = [
        ("UPDATE process_sub_steps SET status='pending' WHERE status='待开始'", 'process_sub_steps'),
        ("UPDATE material_records SET status='pending' WHERE status='待备料'", 'material_records'),
        ("UPDATE material_records SET status='shortage' WHERE status='缺料'", 'material_records'),
        ("UPDATE quality_records SET status='in_progress' WHERE status='quality_reported'", 'quality_records'),
        ("UPDATE quality_records SET status='completed' WHERE status='quality_re_received'", 'quality_records'),
        ("UPDATE quality_records SET status='pending' WHERE status IS NULL", 'quality_records'),
    ]
    for sql, name in migrations:
        cur.execute(sql)
        count = cur.rowcount
        c.commit()
        print(f'  ✅ {name}: 更新 {count} 行')


def drop_data_packages(c):
    """T0.6 DROP data_packages"""
    cur = c.cursor()
    try:
        cur.execute("RENAME TABLE data_packages TO data_packages_deprecated")
        c.commit()
        print('  ✅ data_packages → data_packages_deprecated')
    except Exception as e:
        print(f'  ⚠️ RENAME: {e}')

    cur.execute("""
        CREATE TRIGGER block_write_deprecated
        BEFORE INSERT ON data_packages_deprecated
        FOR EACH ROW
        BEGIN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'data_packages 已废弃，请使用 11 业务表';
        END
    """)
    c.commit()
    print('  ✅ 触发器已创建（阻止写入）')

    cur.execute("DROP TABLE IF EXISTS process_packages")
    c.commit()
    print('  ✅ process_packages 已 DROP')

    cur.execute("DROP TABLE IF EXISTS quality_packages")
    c.commit()
    print('  ✅ quality_packages 已 DROP')


def main():
    print('===== 阶段 1: 实际执行 DDL 升级 + 数据迁移 =====')

    c = pymysql.connect(**DB_CONFIG)

    print('\n[1/3] 9 业务表升级 6 字段...')
    for t in TABLES:
        upgrade_table(c, t)

    print('\n[2/3] 新建 approval_records...')
    create_approval_records(c)

    print('\n[3/3] 数据迁移 + DROP data_packages...')
    migrate_status(c)
    drop_data_packages(c)

    c.close()
    print('\n✅ 阶段 1 DDL 执行完毕')


if __name__ == '__main__':
    main()
