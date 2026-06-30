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

    cursor.execute("SELECT user, host FROM mysql.user WHERE user=%s", (MYSQL_CONFIG['user'],))
    print(f"用户列表 ({MYSQL_CONFIG['user']}):")
    for u in cursor.fetchall():
        print(f"  User: {u[0]}, Host: {u[1]}")

    # 使用安全的方式查询权限（避免SQL注入）
    show_grants_sql = "SHOW GRANTS FOR %s@'%'"
    cursor.execute(show_grants_sql, (MYSQL_CONFIG['user'],))
    print(f"\n权限列表 for {MYSQL_CONFIG['user']}@'%':")
    for g in cursor.fetchall():
        print(f"  {g[0]}")

    conn.close()
    print(f"\n结论: {MYSQL_CONFIG['user']}@'%' 权限检查完成！")
except Exception as e:
    print(f"[ERROR] {e}")
    print("\n提示: 如果MySQL未安装或未启动，请先安装并配置MySQL")