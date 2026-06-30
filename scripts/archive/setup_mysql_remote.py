# -*- coding: utf-8 -*-
import mysql.connector
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db_config import MYSQL_CONFIG

print("正在配置MySQL允许局域网连接...")

try:
    conn = mysql.connector.connect(
        host=MYSQL_CONFIG['host'],
        user=MYSQL_CONFIG['user'],
        password=MYSQL_CONFIG['password'],
        port=MYSQL_CONFIG.get('port', 3306)
    )
    cursor = conn.cursor()

    username = MYSQL_CONFIG['user']
    password = MYSQL_CONFIG['password']
    
    # 使用安全的方式创建用户和授权（避免SQL注入）
    create_user_sql = "CREATE USER IF NOT EXISTS %s@'%' IDENTIFIED BY %s"
    cursor.execute(create_user_sql, (username, password))
    print(f"[OK] 用户创建/已存在: {username}@'%'")

    grant_sql = "GRANT ALL PRIVILEGES ON *.* TO %s@'%' WITH GRANT OPTION"
    cursor.execute(grant_sql, (username,))
    print("[OK] 权限授予成功")

    cursor.execute("FLUSH PRIVILEGES")
    print("[OK] 权限刷新成功")

    conn.close()
    print("\n局域网连接配置完成！")
    print("现在需要修改MySQL配置文件绑定地址为0.0.0.0")
    print("或者在防火墙中开放3306端口")

except Exception as e:
    print(f"[Error] {e}")
    print("\n提示: 如果MySQL未安装或未启动，请先安装并配置MySQL")