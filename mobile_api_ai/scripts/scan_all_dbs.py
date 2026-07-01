# -*- coding: utf-8 -*-
"""扫描 MySQL 所有数据库，找含 products/inventory 的库"""
import os
import pymysql
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(r'd:\yuan\不锈钢网带跟单3.0\.env', override=True)

# 连接（不指定 db）
conn = pymysql.connect(
    host=os.getenv('MYSQL_HOST', '127.0.0.1'),
    port=int(os.getenv('MYSQL_PORT', '3306')),
    user=os.getenv('MYSQL_USER'),
    password=os.getenv('MYSQL_PASSWORD'),
    connect_timeout=5,
    charset='utf8mb4',
)

lines = []
with conn.cursor() as cur:
    cur.execute("SHOW DATABASES")
    dbs = [r[0] for r in cur.fetchall()]
    lines.append(f'ALL DATABASES: {dbs}')

    target_tables = ['products', 'inventory', 'warehouses', 'inbound_records', 'outbound_records', 'stock_records', 'suppliers', 'categories']
    for db in dbs:
        if db in ('information_schema', 'mysql', 'performance_schema', 'sys'):
            continue
        try:
            cur.execute(f"USE `{db}`")
            cur.execute("SHOW TABLES")
            tbls = {list(r.values())[0] if hasattr(r, 'values') else r[0] for r in cur.fetchall()}
            hit = [t for t in target_tables if t in tbls]
            if hit:
                # 查 products 行数
                cnt = {}
                for t in hit:
                    try:
                        cur.execute(f"SELECT COUNT(*) FROM `{t}`")
                        cnt[t] = cur.fetchone()[0]
                    except Exception as e:
                        cnt[t] = f'ERR:{e}'
                lines.append(f'[HIT] {db}: tables={hit}, counts={cnt}')
            else:
                lines.append(f'[skip] {db}: {len(tbls)} tables, no inventory tables')
        except Exception as e:
            lines.append(f'[err] {db}: {e}')

text = '\n'.join(lines)
Path(r'd:\yuan\scan_dbs.txt').write_text(text, encoding='utf-8')
print(text)
conn.close()
