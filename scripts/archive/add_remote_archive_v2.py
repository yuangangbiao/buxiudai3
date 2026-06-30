# -*- coding: utf-8 -*-
"""
数据库归档字段添加 - 分步执行版本
"""
import os
import pymysql
import socket
import time

socket.setdefaulttimeout(60)

_DEFAULT_HOST = os.environ.get('MYSQL_HOST', '')
_DEFAULT_PORT = int(os.environ.get('MYSQL_PORT', '3306'))
_DEFAULT_USER = os.environ.get('MYSQL_USER', 'root')
_DEFAULT_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')

def test_connection():
    config = {
        "host": _DEFAULT_HOST,
        "port": _DEFAULT_PORT,
        "user": _DEFAULT_USER,
        "password": _DEFAULT_PASSWORD,
        "charset": "utf8mb4",
        "connect_timeout": 30,
        "cursorclass": pymysql.cursors.DictCursor
    }

    print("1. 测试连接...")
    conn = pymysql.connect(**config)
    print("   连接成功！")
    cursor = conn.cursor()
    cursor.close()
    conn.close()

def check_and_add_fields():
    config = {
        "host": _DEFAULT_HOST,
        "port": _DEFAULT_PORT,
        "user": _DEFAULT_USER,
        "password": _DEFAULT_PASSWORD,
        "charset": "utf8mb4",
        "connect_timeout": 30,
        "cursorclass": pymysql.cursors.DictCursor
    }

    print("2. 检查现有字段...")
    conn = pymysql.connect(**config)
    cursor = conn.cursor()
    cursor.execute("USE `steel_belt`")
    cursor.execute("DESCRIBE orders")
    columns = [row['Field'] for row in cursor.fetchall()]
    print(f"   当前字段数: {len(columns)}")
    print(f"   归档字段状态:")
    print(f"     - is_archived: {'已存在' if 'is_archived' in columns else '不存在'}")
    print(f"     - archived_at: {'已存在' if 'archived_at' in columns else '不存在'}")
    print(f"     - archived_by: {'已存在' if 'archived_by' in columns else '不存在'}")

    if all(f in columns for f in ['is_archived', 'archived_at', 'archived_by']):
        print("   所有归档字段已存在，无需添加！")
        cursor.close()
        conn.close()
        return True

    print("3. 添加缺失字段...")
    fields_to_add = []
    if 'is_archived' not in columns:
        fields_to_add.append("ADD COLUMN `is_archived` TINYINT(1) DEFAULT 0 COMMENT '归档标记：0-未归档，1-已归档'")
    if 'archived_at' not in columns:
        fields_to_add.append("ADD COLUMN `archived_at` DATETIME DEFAULT NULL COMMENT '归档时间'")
    if 'archived_by' not in columns:
        fields_to_add.append("ADD COLUMN `archived_by` VARCHAR(50) DEFAULT NULL COMMENT '归档人'")

    sql = f"ALTER TABLE orders {', '.join(fields_to_add)}"
    print(f"   执行: ALTER TABLE orders ...")
    cursor.execute(sql)
    conn.commit()
    print("   SQL执行完成")

    cursor.execute("DESCRIBE orders")
    new_columns = [row['Field'] for row in cursor.fetchall()]
    print(f"   添加后字段数: {len(new_columns)}")

    cursor.close()
    conn.close()
    return True

if __name__ == "__main__":
    try:
        test_connection()
        time.sleep(1)
        check_and_add_fields()
        print("\n远程数据库操作完成！")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()