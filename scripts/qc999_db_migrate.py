# QC-999.3: work_order_no → order_no DB列迁移
# 软迁移策略：先加新列 → 数据同步 → 稳定后删旧列
# 执行方式：python scripts/qc999_db_migrate.py --dry-run
#           python scripts/qc999_db_migrate.py --execute

import os, sys, argparse
import sqlite3
import pymysql
from datetime import datetime

# ---- 需要迁移的表 ----
MIGRATIONS = [
    # (表名, 旧列名, 新列名, 列类型)
    ('process_records', 'work_order_no', 'order_no', 'VARCHAR(64)'),
    ('material_requirements', 'work_order_no', 'order_no', 'TEXT'),
    ('work_orders', 'work_order_no', 'order_no', 'VARCHAR(64)'),
    ('production_orders', 'work_order_no', 'order_no', 'VARCHAR(64)'),
    ('quality_records', 'work_order_no', 'order_no', 'VARCHAR(64)'),
]


def migrate_sqlite(db_path: str, dry_run: bool = True):
    """迁移 SQLite 数据库"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in c.fetchall()}

    for table, old_col, new_col, col_type in MIGRATIONS:
        if table not in tables:
            print(f'  SKIP: {table} 不存在')
            continue

        c.execute(f"PRAGMA table_info({table})")
        cols = {row[1] for row in c.fetchall()}

        if old_col not in cols:
            print(f'  SKIP: {table}.{old_col} 不存在')
            continue

        if new_col in cols:
            print(f'  SKIP: {table}.{new_col} 已存在')
            continue

        sql = f"ALTER TABLE {table} ADD COLUMN {new_col} {col_type}"
        print(f'  {"[DRY-RUN]" if dry_run else "[EXEC]"} {sql}')
        if not dry_run:
            c.execute(sql)
            c.execute(f"UPDATE {table} SET {new_col} = {old_col} WHERE {new_col} IS NULL")
            print(f'    数据已同步: {c.rowcount} 行')

    if not dry_run:
        conn.commit()
    conn.close()


def migrate_mysql(db_host: str, db_user: str, db_pass: str, db_name: str, dry_run: bool = True):
    """迁移 MySQL 数据库"""
    conn = pymysql.connect(host=db_host, user=db_user, password=db_pass, database=db_name)
    c = conn.cursor()

    c.execute("SHOW TABLES")
    tables = {row[0] for row in c.fetchall()}

    for table, old_col, new_col, col_type in MIGRATIONS:
        if table not in tables:
            print(f'  SKIP: {table} 不存在')
            continue

        c.execute(f"SHOW COLUMNS FROM {table} LIKE '{old_col}'")
        if not c.fetchone():
            print(f'  SKIP: {table}.{old_col} 不存在')
            continue

        c.execute(f"SHOW COLUMNS FROM {table} LIKE '{new_col}'")
        if c.fetchone():
            print(f'  SKIP: {table}.{new_col} 已存在')
            continue

        sql = f"ALTER TABLE {table} ADD COLUMN {new_col} {col_type} AFTER {old_col}"
        print(f'  {"[DRY-RUN]" if dry_run else "[EXEC]"} {sql}')
        if not dry_run:
            c.execute(sql)
            c.execute(f"UPDATE {table} SET {new_col} = {old_col} WHERE {new_col} IS NULL")
            print(f'    数据已同步: {c.rowcount} 行')

    if not dry_run:
        conn.commit()
    conn.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--dry-run', action='store_true', default=True, help='预览模式（默认）')
    p.add_argument('--execute', dest='dry_run', action='store_false', help='执行模式')
    p.add_argument('--db', choices=['sqlite', 'mysql', 'all'], default='all')
    args = p.parse_args()

    print(f'QC-999.3 DB列迁移: work_order_no → order_no')
    print(f'模式: {"DRY-RUN" if args.dry_run else "EXECUTE"}')
    print(f'时间: {datetime.now().isoformat()}')
    print()

    if args.db in ('sqlite', 'all'):
        db_path = os.getenv('SQLITE_DB_PATH', 'data/steel_belt.db')
        print(f'[SQLite] {db_path}')
        migrate_sqlite(db_path, args.dry_run)

    if args.db in ('mysql', 'all'):
        print(f'[MySQL] {os.getenv("MYSQL_DATABASE", "steel_belt")}')
        migrate_mysql(
            os.getenv('MYSQL_HOST', 'localhost'),
            os.getenv('MYSQL_USER', 'root'),
            os.getenv('MYSQL_PASSWORD', ''),
            os.getenv('MYSQL_DATABASE', 'steel_belt'),
            args.dry_run,
        )

    print('\n完成。' + (' 执行 --execute 进行实际迁移。' if args.dry_run else ''))
