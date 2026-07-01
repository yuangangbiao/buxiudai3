# -*- coding: utf-8 -*-
"""扫描 container_center + steel_belt 库的 products 表，看是否有 001 迁移特征字段
（last_purchase_price, last_purchase_price_at, deleted_at, users, notifications 等）"""
import os
import pymysql
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(r'd:\yuan\不锈钢网带跟单3.0\.env', override=True)

# 001 迁移特征
key_fields = ['last_purchase_price', 'last_purchase_price_at', 'deleted_at', 'status', 'max_stock']
key_tables = ['users', 'notifications', 'import_sessions', 'stocktakes', 'transfers']

conn = pymysql.connect(
    host=os.getenv('MYSQL_HOST'), port=int(os.getenv('MYSQL_PORT')),
    user=os.getenv('MYSQL_USER'), password=os.getenv('MYSQL_PASSWORD'),
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor,
)
lines = ['=== 前期 001 迁移脚本的库归属审计 ===', '']

target_dbs = ['container_center', 'steel_belt']
with conn.cursor() as cur:
    for db in target_dbs:
        cur.execute(f"USE `{db}`")
        lines.append(f'[{db}]')
        # products 字段
        cur.execute("SHOW TABLES LIKE 'products'")
        if cur.fetchone():
            cur.execute("DESCRIBE products")
            cols = {r['Field']: r for r in cur.fetchall()}
            hit = [f for f in key_fields if f in cols]
            lines.append(f'  products 字段数: {len(cols)}')
            lines.append(f'  001 特征字段命中: {hit if hit else "无"}')
        else:
            lines.append('  products 表: 不存在')
        # 关键表
        for t in key_tables:
            cur.execute(f"SHOW TABLES LIKE '{t}'")
            if cur.fetchone():
                cur.execute(f"SELECT COUNT(*) AS n FROM `{t}`")
                n = cur.fetchone()['n']
                lines.append(f'  表 {t}: 存在 ({n} 行)')
            else:
                lines.append(f'  表 {t}: 不存在')
        # 找 001 创建的索引
        cur.execute("SHOW INDEX FROM products WHERE Key_name='uk_products_code_active'")
        if cur.fetchone():
            lines.append('  索引 uk_products_code_active: 存在 ✅ 001 已跑过此库')
        else:
            lines.append('  索引 uk_products_code_active: 不存在 ❌ 001 未跑过此库')
        lines.append('')

text = '\n'.join(lines)
Path(r'd:\yuan\audit_001_db.txt').write_text(text, encoding='utf-8')
print(text)
conn.close()
