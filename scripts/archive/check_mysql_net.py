# -*- coding: utf-8 -*-
import mysql.connector
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db_config import MYSQL_CONFIG

try:
    conn = mysql.connector.connect(
        host=MYSQL_CONFIG['host'],
        user=MYSQL_CONFIG['user'],
        password=MYSQL_CONFIG['password'],
        port=MYSQL_CONFIG.get('port', 3306)
    )
    cursor = conn.cursor()

    cursor.execute("SHOW VARIABLES LIKE 'skip_networking'")
    print("skip_networking:", cursor.fetchall())

    cursor.execute("SHOW VARIABLES LIKE 'bind_address'")
    print("bind_address:", cursor.fetchall())

    conn.close()
except Exception as e:
    print(f"[ERROR] {e}")
    print("\n提示: 如果MySQL未安装或未启动，请先安装并配置MySQL")