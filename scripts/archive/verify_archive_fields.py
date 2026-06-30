# -*- coding: utf-8 -*-
"""
验证归档字段是否存在
"""
import os
import pymysql
import socket

socket.setdefaulttimeout(30)

_DEFAULT_HOST = os.environ.get('MYSQL_HOST', '')
_DEFAULT_PORT = int(os.environ.get('MYSQL_PORT', '3306'))
_DEFAULT_USER = os.environ.get('MYSQL_USER', 'root')
_DEFAULT_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')

def check_remote():
    config = {
        "host": _DEFAULT_HOST,
        "port": _DEFAULT_PORT,
        "user": _DEFAULT_USER,
        "password": _DEFAULT_PASSWORD,
        "charset": "utf8mb4",
        "connect_timeout": 30,
        "cursorclass": pymysql.cursors.DictCursor
    }

    print("检查远程数据库 orders 表归档字段...")
    conn = pymysql.connect(**config)
    cursor = conn.cursor()
    cursor.execute("USE `steel_belt`")
    cursor.execute("DESCRIBE orders")
    columns = {row['Field']: row for row in cursor.fetchall()}

    archive_fields = ['is_archived', 'archived_at', 'archived_by']
    for field in archive_fields:
        if field in columns:
            info = columns[field]
            print(f"  ✓ {field}: {info['Type']} - {info.get('Comment', '')}")
        else:
            print(f"  ✗ {field}: 不存在!")

    print(f"\n总字段数: {len(columns)}")
    cursor.close()
    conn.close()

def check_local():
    config = {
        "host": "localhost",
        "port": _DEFAULT_PORT,
        "user": _DEFAULT_USER,
        "password": _DEFAULT_PASSWORD,
        "charset": "utf8mb4",
        "connect_timeout": 15,
        "cursorclass": pymysql.cursors.DictCursor
    }

    print("\n检查本地数据库 orders 表归档字段...")
    conn = pymysql.connect(**config)
    cursor = conn.cursor()
    cursor.execute("USE `steel_belt`")
    cursor.execute("DESCRIBE orders")
    columns = {row['Field']: row for row in cursor.fetchall()}

    archive_fields = ['is_archived', 'archived_at', 'archived_by']
    for field in archive_fields:
        if field in columns:
            info = columns[field]
            print(f"  ✓ {field}: {info['Type']} - {info.get('Comment', '')}")
        else:
            print(f"  ✗ {field}: 不存在!")

    print(f"\n总字段数: {len(columns)}")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    check_remote()
    check_local()