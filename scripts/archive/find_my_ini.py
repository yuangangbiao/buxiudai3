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

    cursor.execute("SHOW VARIABLES LIKE 'datadir'")
    result = cursor.fetchone()
    print("datadir:", result)

    if result:
        datadir = result[1]
        myini = os.path.join(os.path.dirname(datadir), 'my.ini')
        print("my.ini location:", myini)
        if os.path.exists(myini):
            print("[OK] my.ini exists")
        else:
            print("[NOT FOUND] my.ini not at expected location")
            for path in [
                r"C:\ProgramData\MySQL\MySQL Server 5.7\my.ini",
                r"C:\ProgramData\MySQL\MySQL Server 8.0\my.ini",
                r"C:\MySQL\my.ini",
            ]:
                if os.path.exists(path):
                    print("Found at:", path)
                    break

    conn.close()
except Exception as e:
    print(f"[ERROR] {e}")
    print("\n提示: 如果MySQL未安装或未启动，请先安装并配置MySQL")