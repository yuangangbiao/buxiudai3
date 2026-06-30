# -*- coding: utf-8 -*-
"""检查相关表结构"""
import pymysql

CC_CONFIG = {
    'host': 'localhost', 'user': 'root', 'password': '88888888',
    'database': 'container_center', 'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

STEEL_CONFIG = {
    'host': 'localhost', 'user': 'root', 'password': '88888888',
    'database': 'steel_belt', 'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}


def show_table_columns(config, db_name, table):
    conn = pymysql.connect(**config)
    try:
        with conn.cursor() as c:
            c.execute(f"SHOW COLUMNS FROM {table}")
            cols = c.fetchall()
            print(f"\n=== {db_name}.{table} ===")
            for col in cols:
                print(f"  {col['Field']:30s} {col['Type']:20s} {col['Key']:10s} {col['Extra']}")
    finally:
        conn.close()


# process_sub_steps
show_table_columns(STEEL_CONFIG, 'steel_belt', 'process_sub_steps')

# process_records
show_table_columns(STEEL_CONFIG, 'steel_belt', 'process_records')

# report_queue
show_table_columns(CC_CONFIG, 'container_center', 'report_queue')
