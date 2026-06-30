# -*- coding: utf-8 -*-
"""
数据库归档字段添加脚本
为 orders 表添加归档相关字段
"""
import os
import sys
import socket

socket.setdefaulttimeout(30)

def get_remote_config():
    """获取远程数据库配置"""
    return {
        "host": os.environ.get('MYSQL_HOST', ''),
        "port": int(os.environ.get('MYSQL_PORT', '3306')),
        "user": os.environ.get('MYSQL_USER', 'root'),
        "password": os.environ.get('MYSQL_PASSWORD', ''),
        "charset": "utf8mb4",
        "connect_timeout": 30
    }

def get_local_config():
    """获取本地数据库配置"""
    return {
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "password": os.environ.get('MYSQL_PASSWORD', ''),
        "charset": "utf8mb4",
        "connect_timeout": 10
    }

def add_archive_fields(config, db_name='steel_belt'):
    """
    为 orders 表添加归档字段
    """
    import pymysql

    try:
        config['cursorclass'] = pymysql.cursors.DictCursor
        conn = pymysql.connect(**config)
        cursor = conn.cursor()

        cursor.execute(f"USE `{db_name}`")

        cursor.execute("DESCRIBE orders")
        existing_columns = [row['Field'] for row in cursor.fetchall()]

        print(f"  当前 orders 表字段数量: {len(existing_columns)}")

        fields_to_add = []
        field_descriptions = []

        if 'is_archived' not in existing_columns:
            fields_to_add.append("ADD COLUMN `is_archived` TINYINT(1) DEFAULT 0 COMMENT '归档标记：0-未归档，1-已归档'")
            field_descriptions.append("is_archived")
            print("    + is_archived 字段")

        if 'archived_at' not in existing_columns:
            fields_to_add.append("ADD COLUMN `archived_at` DATETIME DEFAULT NULL COMMENT '归档时间'")
            field_descriptions.append("archived_at")
            print("    + archived_at 字段")

        if 'archived_by' not in existing_columns:
            fields_to_add.append("ADD COLUMN `archived_by` VARCHAR(50) DEFAULT NULL COMMENT '归档人'")
            field_descriptions.append("archived_by")
            print("    + archived_by 字段")

        if not fields_to_add:
            print("  ✓ orders 表已有归档字段，无需添加")
            cursor.close()
            conn.close()
            return True

        print(f"\n  正在添加 {len(fields_to_add)} 个字段...")
        sql = f"ALTER TABLE orders {', '.join(fields_to_add)}"
        cursor.execute(sql)
        conn.commit()
        print("  ✓ SQL执行完成")

        cursor.execute("DESCRIBE orders")
        new_columns = [row['Field'] for row in cursor.fetchall()]
        print(f"\n  ✓ 字段添加成功！")
        print(f"  orders 表现有字段数量: {len(new_columns)}")

        new_archive_fields = [f for f in new_columns if f in ('is_archived', 'archived_at', 'archived_by')]
        print(f"  新增归档字段: {', '.join(new_archive_fields)}")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"  ✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("数据库归档字段添加工具")
    print("=" * 60)

    print("\n" + "=" * 60)
    print("开始添加到远程数据库 (192.168.0.101)...")
    print("=" * 60)
    remote_config = get_remote_config()
    print(f"  连接到 {remote_config['host']}:{remote_config['port']}...")
    remote_result = add_archive_fields(remote_config)

    print("\n" + "=" * 60)
    print("开始添加到本地数据库 (localhost)...")
    print("=" * 60)
    local_config = get_local_config()
    print(f"  连接到 {local_config['host']}:{local_config['port']}...")
    local_result = add_archive_fields(local_config)

    print("\n" + "=" * 60)
    print("执行结果汇总")
    print("=" * 60)
    print(f"远程数据库 (192.168.0.101): {'✓ 成功' if remote_result else '✗ 失败'}")
    print(f"本地数据库 (localhost): {'✓ 成功' if local_result else '✗ 失败'}")

if __name__ == "__main__":
    main()