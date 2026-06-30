# -*- coding: utf-8 -*-
"""
数据库归档字段添加 - 远程数据库
"""
import pymysql
import socket

socket.setdefaulttimeout(30)

def add_remote():
    config = {
        "host": "192.168.0.101",
        "port": 3306,
        "user": "root",
        "password": os.environ.get('MYSQL_PASSWORD', ''),
        "charset": "utf8mb4",
        "connect_timeout": 30,
        "cursorclass": pymysql.cursors.DictCursor
    }

    print("连接到远程数据库 192.168.0.101:3306...")
    conn = pymysql.connect(**config)
    cursor = conn.cursor()
    cursor.execute("USE `steel_belt`")

    cursor.execute("DESCRIBE orders")
    existing_columns = [row['Field'] for row in cursor.fetchall()]
    print(f"orders 表现有字段: {len(existing_columns)}")

    fields_to_add = []

    if 'is_archived' not in existing_columns:
        fields_to_add.append("ADD COLUMN `is_archived` TINYINT(1) DEFAULT 0 COMMENT '归档标记：0-未归档，1-已归档'")
        print("  + is_archived")

    if 'archived_at' not in existing_columns:
        fields_to_add.append("ADD COLUMN `archived_at` DATETIME DEFAULT NULL COMMENT '归档时间'")
        print("  + archived_at")

    if 'archived_by' not in existing_columns:
        fields_to_add.append("ADD COLUMN `archived_by` VARCHAR(50) DEFAULT NULL COMMENT '归档人'")
        print("  + archived_by")

    if not fields_to_add:
        print("无需添加字段（已存在）")
    else:
        print(f"正在添加 {len(fields_to_add)} 个字段...")
        sql = f"ALTER TABLE orders {', '.join(fields_to_add)}"
        cursor.execute(sql)
        conn.commit()
        print("远程数据库字段添加成功！")

        cursor.execute("DESCRIBE orders")
        new_columns = [row['Field'] for row in cursor.fetchall()]
        print(f"orders 表现有字段数: {len(new_columns)}")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    add_remote()