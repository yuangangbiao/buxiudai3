# -*- coding: utf-8 -*-
"""
[v3.6] 阶段 1 修复 - 给业务表加 4 字段（is_deleted/created_by/updated_by/updated_at）
"""
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


def check_and_add(c, table, field, definition):
    cur = c.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM information_schema.columns "
        "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND COLUMN_NAME=%s",
        ('container_center', table, field)
    )
    exists = cur.fetchone()[0] > 0
    if not exists:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {field} {definition}")
        c.commit()
        print(f'  ✅ {table}: 加 {field}')
    else:
        print(f'  ⏭ {table}: {field} 已存在')


def main():
    print('===== 阶段 1 修复: 加 4 字段到 9 业务表 =====')
    c = pymysql.connect(**DB_CONFIG)

    fields = [
        ('is_deleted', 'TINYINT(1) NOT NULL DEFAULT 0'),
        ('created_by', "VARCHAR(64) NOT NULL DEFAULT 'system'"),
        ('updated_by', "VARCHAR(64) NOT NULL DEFAULT 'system'"),
        ('updated_at', 'DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'),
    ]

    for table in TABLES:
        print(f'\n[{table}]')
        for field, definition in fields:
            try:
                check_and_add(c, table, field, definition)
            except Exception as e:
                print(f'  ❌ {table}.{field}: {e}')

    c.close()
    print('\n✅ 修复完成')


if __name__ == '__main__':
    main()
