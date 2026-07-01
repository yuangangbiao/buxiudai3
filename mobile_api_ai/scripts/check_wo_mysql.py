# -*- coding: utf-8 -*-
"""鏌?WO-202605006 MySQL 瀹屾暣璁㈠崟"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import os
from dotenv import load_dotenv
load_dotenv('d:/yuan/涓嶉攬閽㈢綉甯﹁窡鍗?.0/mobile_api_ai/.env')

import pymysql
from pymysql.cursors import DictCursor

cfg = {
    'host': os.environ.get('MYSQL_HOST', ''),
    'port': int(os.environ.get('MYSQL_PORT', 3306)),
    'user': os.environ.get('MYSQL_USER', 'root'),
    'password': os.environ.get('MYSQL_PASSWORD', ''),
    'database': os.environ.get('MYSQL_DATABASE', 'steel_belt'),
    'charset': 'utf8mb4',
}

conn = pymysql.connect(**cfg, cursorclass=DictCursor)
c = conn.cursor()

for tbl, col, val in [('orders', 'order_no', 'WO-202605006'),
                        ('production_orders', 'order_no', 'WO-202605006')]:
    print(f'\n=== MySQL.{tbl} ===')
    c.execute(f"SELECT * FROM {tbl} WHERE {col}=%s", (val,))
    row = c.fetchone()
    if row:
        for k, v in row.items():
            print(f'  {k}: {v}')
    else:
        print('  NOT FOUND')

# 涔熸煡 ORD-202604290001
print('\n=== MySQL.orders ORD-202604290001 ===')
c.execute("SELECT * FROM orders WHERE order_no=%s", ('ORD-202604290001',))
row = c.fetchone()
if row:
    for k, v in row.items():
        print(f'  {k}: {v}')

conn.close()
