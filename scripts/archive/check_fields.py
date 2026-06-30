# -*- coding: utf-8 -*-
import pymysql
import os
from dotenv import load_dotenv
load_dotenv('.env')

config = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'port': int(os.getenv('MYSQL_PORT', '3306')),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', ''),
    'database': os.getenv('MYSQL_DATABASE', 'steel_belt'),
    'charset': 'utf8mb4'
}

conn = pymysql.connect(**config)
cursor = conn.cursor()

# 创建db_version表
cursor.execute("""
CREATE TABLE IF NOT EXISTS db_version (
    id INT AUTO_INCREMENT PRIMARY KEY,
    version VARCHAR(32) NOT NULL UNIQUE,
    applied_at DATETIME NOT NULL,
    description TEXT,
    checksum VARCHAR(64)
)
""")
conn.commit()
print("db_version表已创建")

# 插入升级记录
from datetime import datetime
cursor.execute("""
INSERT INTO db_version (version, applied_at, description, checksum)
VALUES (%s, %s, %s, %s)
""", ("1.0.0", datetime.now(), "添加订单归档功能字段", "manual"))
conn.commit()
print("v1.0.0升级记录已插入")

# 验证
cursor.execute("SELECT * FROM db_version")
for row in cursor.fetchall():
    print(f"  版本: {row[1]}, 时间: {row[2]}")

cursor.close()
conn.close()
