# -*- coding: utf-8 -*-
"""看 inventory_db 实际所有表 + products/inventory 数据样本"""
import os
import pymysql
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(r'd:\yuan\不锈钢网带跟单3.0\.env', override=True)
conn = pymysql.connect(
    host=os.getenv('MYSQL_HOST'), port=int(os.getenv('MYSQL_PORT')),
    user=os.getenv('MYSQL_USER'), password=os.getenv('MYSQL_PASSWORD'),
    database='inventory_db', charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor,
)
lines = []
with conn.cursor() as cur:
    cur.execute("SHOW TABLES")
    tbls = [list(r.values())[0] for r in cur.fetchall()]
    lines.append(f'inventory_db TABLES ({len(tbls)}):')
    for t in tbls:
        cur.execute(f"SELECT COUNT(*) AS n FROM `{t}`")
        n = cur.fetchone()['n']
        lines.append(f'  {t}: {n} rows')
    # products 字段 + 样本
    cur.execute("DESCRIBE products")
    cols = [r['Field'] for r in cur.fetchall()]
    lines.append(f'products 字段: {cols}')
    cur.execute("SELECT * FROM products LIMIT 2")
    rows = cur.fetchall()
    lines.append(f'products 样本: {rows}')
conn.close()
text = '\n'.join(lines)
Path(r'd:\yuan\inv_db_detail.txt').write_text(text, encoding='utf-8')
print(text)
