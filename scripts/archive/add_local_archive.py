# -*- coding: utf-8 -*-
"""
数据库归档字段添加 - 本地数据库
"""
import pymysql
import socket

socket.setdefaulttimeout(30)

def add_local():
    config = {
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "password": os.environ.get('MYSQL_PASSWORD', ''),
        "charset": "utf8mb4",
        "connect_timeout": 15,
        "cursorclass": pymysql.cursors.DictCursor
    }

    print("连接到本地数据库 localhost:3306...")
    conn = pymysql.connect(**config)
    print("连接成功！")
    cursor = conn.cursor()

    try:
        cursor.execute("USE `steel_belt`")
    except Exception as e:
        print(f"steel_belt 数据库不存在 (错误: {e})，尝试其他数据库...")
        cursor.execute("SHOW DATABASES")
        dbs = [list(row)[0] for row in cursor.fetchall()]
        print(f"可用数据库: {dbs}")
        return

    cursor.execute("DESCRIBE orders")
    columns = [row['Field'] for row in cursor.fetchall()]
    print(f"orders 表现有字段: {len(columns)}")
    print(f"归档字段状态:")
    print(f"  - is_archived: {'已存在' if 'is_archived' in columns else '不存在'}")
    print(f"  - archived_at: {'已存在' if 'archived_at' in columns else '不存在'}")
    print(f"  - archived_by: {'已存在' if 'archived_by' in columns else '不存在'}")

    if all(f in columns for f in ['is_archived', 'archived_at', 'archived_by']):
        print("所有归档字段已存在，无需添加！")
    else:
        fields_to_add = []
        if 'is_archived' not in columns:
            fields_to_add.append("ADD COLUMN `is_archived` TINYINT(1) DEFAULT 0 COMMENT '归档标记'")
        if 'archived_at' not in columns:
            fields_to_add.append("ADD COLUMN `archived_at` DATETIME DEFAULT NULL COMMENT '归档时间'")
        if 'archived_by' not in columns:
            fields_to_add.append("ADD COLUMN `archived_by` VARCHAR(50) DEFAULT NULL COMMENT '归档人'")

        sql = f"ALTER TABLE orders {', '.join(fields_to_add)}"
        print(f"正在添加 {len(fields_to_add)} 个字段...")
        cursor.execute(sql)
        conn.commit()
        print("本地数据库字段添加成功！")

        cursor.execute("DESCRIBE orders")
        new_columns = [row['Field'] for row in cursor.fetchall()]
        print(f"添加后字段数: {len(new_columns)}")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    try:
        add_local()
        print("\n本地数据库操作完成！")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()