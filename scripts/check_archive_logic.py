# -*- coding: utf-8 -*-
import sys
import os

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_DIR, '.env'))

import pymysql

conn = pymysql.connect(
    host=os.getenv('MYSQL_HOST', 'localhost'),
    port=int(os.getenv('MYSQL_PORT', 3306)),
    user=os.getenv('MYSQL_USER', 'root'),
    password=os.getenv('MYSQL_PASSWORD', ''),
    database=os.getenv('MYSQL_DATABASE', 'steel_belt'),
    charset='utf8mb4'
)

cursor = conn.cursor(pymysql.cursors.DictCursor)

# 查看 orders 表结构
print("=== orders 表结构 ===")
cursor.execute("DESCRIBE orders")
cols = cursor.fetchall()
for c in cols:
    print(f"  {c['Field']}: {c['Type']}, Null={c['Null']}, Key={c['Key']}, Default={c['Default']}")

# 查找归档相关的代码
print("\n=== 查找归档相关代码 ===")

conn.close()

# 搜索代码中的归档逻辑
import os
import re

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

for root, dirs, files in os.walk(PROJECT_DIR):
    # 跳过非代码目录
    if any(skip in root for skip in ['__pycache__', '.git', 'node_modules', '.venv']):
        continue
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'archive' in content.lower() or '归档' in content:
                        # 查找相关行
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if 'archive' in line.lower() or '归档' in line:
                                print(f"\n{filepath}:{i+1}")
                                print(f"  {line.strip()}")
            except Exception as e:
                print(f"[check_archive_logic] 处理文件 {filepath} 失败: {e}")