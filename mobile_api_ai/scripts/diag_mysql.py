# -*- coding: utf-8 -*-
"""直接测 MySQL 连接 + 看 products 表"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import pymysql
from pymysql.cursors import DictCursor

load_dotenv(r'd:\yuan\不锈钢网带跟单3.0\.env', override=True)

cfg = {
    'host': os.getenv('MYSQL_HOST', '127.0.0.1'),
    'port': int(os.getenv('MYSQL_PORT', '3306')),
    'user': os.getenv('MYSQL_USER'),
    'password': os.getenv('MYSQL_PASSWORD'),
    'database': os.getenv('INVENTORY_DB_NAME'),
    'charset': os.getenv('MYSQL_CHARSET', 'utf8mb4'),
    'cursorclass': DictCursor,
}
result_lines = ['CFG: ' + str({k: (v if k != "password" else "***") for k, v in cfg.items()})]

try:
    conn = pymysql.connect(**cfg, connect_timeout=5)
    result_lines.append('MySQL CONNECTED')
    with conn.cursor() as cur:
        # 库中所有表
        cur.execute("SHOW TABLES")
        tables = [list(r.values())[0] for r in cur.fetchall()]
        result_lines.append(f'TABLES ({len(tables)}): ' + ', '.join(tables[:20]))

        # products 表数据量
        for tbl in ['products', 'inventory', 'warehouses', 'stock', 'inbound', 'outbound', 'inbound_records', 'outbound_records']:
            try:
                cur.execute(f"SELECT COUNT(*) AS n FROM {tbl}")
                n = cur.fetchone()
                result_lines.append(f'  {tbl}: {n}')
            except Exception as e:
                result_lines.append(f'  {tbl}: ERR {str(e)[:60]}')

        # 看 products 前 3 行
        try:
            cur.execute("SELECT id, code, name, stock, deleted_at FROM products WHERE deleted_at IS NULL LIMIT 3")
            rows = cur.fetchall()
            result_lines.append(f'PRODUCTS (sample): {rows}')
        except Exception as e:
            result_lines.append(f'PRODUCTS ERR: {str(e)[:100]}')
    conn.close()
except Exception as e:
    result_lines.append(f'CONNECT ERR: {type(e).__name__}: {e}')

text = '\n'.join(result_lines)
Path(r'd:\yuan\mysql_test.txt').write_text(text, encoding='utf-8')
print(text)
