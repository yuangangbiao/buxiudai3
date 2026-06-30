# -*- coding: utf-8 -*-
"""
DDL: 为 process_records 表添加 process_code 字段

日期: 2026-06-16
功能: 支持自定义工序插入
"""
import os
import sys
import pymysql

# 数据库配置
DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", "88888888"),
    "database": os.getenv("MYSQL_DATABASE", "steel_belt"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}


def get_connection():
    return pymysql.connect(**DB_CONFIG)


def run_migration():
    """执行迁移"""
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # 1. 检查字段是否已存在
        cursor.execute("DESCRIBE process_records")
        columns = [row['Field'] for row in cursor.fetchall()]

        # 2. 添加 process_code 字段
        if 'process_code' not in columns:
            print("[DDL] 添加 process_code 字段...")
            cursor.execute("""
                ALTER TABLE process_records
                ADD COLUMN process_code VARCHAR(32) DEFAULT NULL COMMENT '工序编码 P01/P03-B'
            """)
            print("[DDL] process_code 字段已添加")
        else:
            print("[DDL] process_code 字段已存在，跳过")

        # 3. 检查 is_deleted_code 字段是否已存在
        if 'is_deleted_code' not in columns:
            print("[DDL] 添加 is_deleted_code 字段...")
            cursor.execute("""
                ALTER TABLE process_records
                ADD COLUMN is_deleted_code TINYINT(1) DEFAULT 0 COMMENT '软删除标记（用于编号回收）'
            """)
            print("[DDL] is_deleted_code 字段已添加")
        else:
            print("[DDL] is_deleted_code 字段已存在，跳过")

        conn.commit()

        # 4. 初始化基准工序的 process_code
        print("[DDL] 初始化基准工序的 process_code...")
        cursor.execute("""
            UPDATE process_records
            SET process_code = CONCAT('P', LPAD(process_seq, 2, '0'))
            WHERE process_code IS NULL AND process_seq IS NOT NULL
        """)
        updated = cursor.rowcount
        print(f"[DDL] 已初始化 {updated} 条基准工序")

        conn.commit()

        # 5. 验证
        cursor.execute("SELECT COUNT(*) as cnt FROM process_records WHERE process_code IS NOT NULL")
        result = cursor.fetchone()
        print(f"[DDL] 当前有 process_code 的记录数: {result['cnt']}")

        cursor.close()
        print("[DDL] 迁移完成!")

        return True

    except Exception as e:
        print(f"[DDL] 迁移失败: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    print("=" * 50)
    print("DDL: 添加 process_code 字段")
    print("=" * 50)
    success = run_migration()
    sys.exit(0 if success else 1)
