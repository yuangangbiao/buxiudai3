# -*- coding: utf-8 -*-
"""检查MySQL数据库"""
import pymysql
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db_config import MYSQL_CONFIG

try:
    conn = pymysql.connect(
        host=MYSQL_CONFIG['host'],
        user=MYSQL_CONFIG['user'],
        password=MYSQL_CONFIG['password'],
        port=MYSQL_CONFIG.get('port', 3306)
    )
    cursor = conn.cursor()
    cursor.execute('SHOW DATABASES')
    print("=" * 50)
    print("MySQL 数据库列表:")
    print("=" * 50)
    for r in cursor.fetchall():
        db_name = r[0]
        is_ours = " <-- 库存系统" if db_name == 'inventory_management_db' else ""
        is_ours += " <-- 跟单系统" if db_name == 'inventory_db' else ""
        is_ours += " <-- 钢带系统" if db_name == MYSQL_CONFIG.get('database', 'steel_belt') else ""
        print(f"  - {db_name}{is_ours}")
    print("=" * 50)

    cursor.close()
    conn.close()
    print("\n[OK] MySQL连接正常")
except Exception as e:
    print(f"[ERROR] {e}")
    print("\n提示: 如果MySQL未安装或未启动，请先安装并配置MySQL")