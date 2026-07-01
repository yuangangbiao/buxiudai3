# -*- coding: utf-8 -*-
"""最小化审计：001 迁移特征库归属"""
import os
import pymysql
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(r'd:\yuan\不锈钢网带跟单3.0\.env', override=True)

key_fields = ['last_purchase_price', 'last_purchase_price_at', 'deleted_at', 'max_stock']
key_tables = ['users', 'notifications', 'import_sessions', 'stocktakes', 'transfers', 'transfer_items', 'stocktake_items']

conn = pymysql.connect(
    host=os.getenv('MYSQL_HOST'), port=int(os.getenv('MYSQL_PORT')),
    user=os.getenv('MYSQL_USER'), password=os.getenv('MYSQL_PASSWORD'),
    charset='utf8mb4',
)

lines = ['=== 001 迁移特征库归属审计 ===', '']
cur = conn.cursor()
for db in ['container_center', 'steel_belt']:
    try:
        cur.execute(f"USE `{db}`")
    except Exception as e:
        lines.append(f'[{db}] ERR: {e}'); continue
    lines.append(f'[{db}]')
    try:
        cur.execute("SHOW TABLES LIKE 'products'")
        if cur.fetchone():
            cur.execute("DESCRIBE products")
            cols = [r[0] for r in cur.fetchall()]
            hit = [f for f in key_fields if f in cols]
            lines.append(f'  products 字段数: {len(cols)}')
            lines.append(f'  001 特征字段: {hit if hit else "无"}')
            cur.execute("SHOW INDEX FROM products WHERE Key_name='uk_products_code_active'")
            idx_hit = bool(cur.fetchone())
            lines.append(f'  索引 uk_products_code_active: {"存在" if idx_hit else "不存在"}')
        else:
            lines.append('  products 表: 不存在')
    except Exception as e:
        lines.append(f'  products ERR: {e}')

    for t in key_tables:
        cur.execute(f"SHOW TABLES LIKE '{t}'")
        if cur.fetchone():
            cur.execute(f"SELECT COUNT(*) FROM `{t}`")
            n = cur.fetchone()[0]
            lines.append(f'  表 {t}: 存在 ({n} 行)')
    lines.append('')

conn.close()
text = '\n'.join(lines)
Path(r'd:\yuan\audit_001.txt').write_text(text, encoding='utf-8')
print(text)
