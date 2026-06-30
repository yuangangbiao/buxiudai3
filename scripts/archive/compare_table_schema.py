# -*- coding: utf-8 -*-
"""对比两个数据库的 production_orders 表结构"""

import os
import sys

project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(project_dir, '.env'))

import pymysql

# 远程数据库 192.168.0.101
REMOTE_HOST = '192.168.0.101'
REMOTE_PORT = 3306
REMOTE_USER = 'root'
REMOTE_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')

# 本地数据库配置 (使用 .env)
LOCAL_HOST = os.getenv('MYSQL_HOST', 'localhost')
LOCAL_PORT = int(os.getenv('MYSQL_PORT', 3306))
LOCAL_USER = os.getenv('MYSQL_USER', 'root')
LOCAL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
LOCAL_DATABASE = os.getenv('MYSQL_DATABASE', 'steel_belt')

def get_table_fields(conn, database, table):
    """获取表的字段列表"""
    cursor = conn.cursor()
    cursor.execute(f"USE {database}")
    cursor.execute(f"DESCRIBE {table}")
    cols = cursor.fetchall()
    cursor.close()
    return {col['Field']: col['Type'] for col in cols}

print("=" * 60)
print("对比两个数据库的 production_orders 表结构")
print("=" * 60)
print()

try:
    # 连接远程数据库
    print(f"1. 连接远程数据库 {REMOTE_HOST}...")
    remote_conn = pymysql.connect(
        host=REMOTE_HOST, port=REMOTE_PORT, user=REMOTE_USER,
        password=REMOTE_PASSWORD, charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    remote_fields = get_table_fields(remote_conn, 'steel_belt', 'production_orders')
    remote_conn.close()
    print(f"   ✓ 远程表有 {len(remote_fields)} 个字段")

    # 连接本地数据库
    print(f"2. 连接本地数据库 {LOCAL_HOST}...")
    local_conn = pymysql.connect(
        host=LOCAL_HOST, port=LOCAL_PORT, user=LOCAL_USER,
        password=LOCAL_PASSWORD, charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    local_fields = get_table_fields(local_conn, LOCAL_DATABASE, 'production_orders')
    local_conn.close()
    print(f"   ✓ 本地表有 {len(local_fields)} 个字段")

    print()
    print("=" * 60)
    print("字段对比")
    print("=" * 60)

    # 远程有，本地没有的
    remote_only = set(remote_fields.keys()) - set(local_fields.keys())
    if remote_only:
        print(f"\n❌ 远程有但本地没有的字段 ({len(remote_only)} 个):")
        for f in sorted(remote_only):
            print(f"   + {f} ({remote_fields[f]})")

    # 本地有，远程没有的
    local_only = set(local_fields.keys()) - set(remote_fields.keys())
    if local_only:
        print(f"\n❌ 本地有但远程没有的字段 ({len(local_only)} 个):")
        for f in sorted(local_only):
            print(f"   + {f} ({local_fields[f]})")

    if not remote_only and not local_only:
        print("\n✓ 两个数据库字段完全相同")

    print()
    print("=" * 60)
    print("字段详情")
    print("=" * 60)
    print(f"\n远程 ({REMOTE_HOST}) 字段:")
    for f, t in sorted(remote_fields.items()):
        print(f"   {f}: {t}")

except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
