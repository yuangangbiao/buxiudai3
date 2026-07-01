# -*- coding: utf-8 -*-
"""确认所有写入/备份都在 inventory_db 库"""
import os
import pymysql
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(r'd:\yuan\不锈钢网带跟单3.0\.env', override=True)

# 1) 连 inventory_db 看备份表 + 迁移结果
conn = pymysql.connect(
    host=os.getenv('MYSQL_HOST'), port=int(os.getenv('MYSQL_PORT')),
    user=os.getenv('MYSQL_USER'), password=os.getenv('MYSQL_PASSWORD'),
    database='inventory_db', charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor,
)
lines = ['=== 写入操作汇总 ===', '全部在 inventory_db 库', '']

with conn.cursor() as cur:
    cur.execute("SHOW TABLES")
    tbls = [list(r.values())[0] for r in cur.fetchall()]
    lines.append(f'[1] inventory_db 库当前共 {len(tbls)} 张表：')
    for t in sorted(tbls):
        if '_backup_' in t or t.startswith('_'):
            cur.execute(f"SELECT COUNT(*) AS n FROM `{t}`")
            n = cur.fetchone()['n']
            lines.append(f'    [备份] {t} ({n} 行)')
        else:
            cur.execute(f"SELECT COUNT(*) AS n FROM `{t}`")
            n = cur.fetchone()['n']
            lines.append(f'    {t} ({n} 行)')

    # 2) 关键数据抽样
    lines.append('')
    lines.append('[2] 业务表数据样本：')
    cur.execute("SELECT id, code, name, spec, price, deleted_at FROM products WHERE deleted_at IS NULL LIMIT 3")
    lines.append(f'  products: {cur.fetchall()}')
    cur.execute("SELECT * FROM inventory LIMIT 2")
    lines.append(f'  inventory: {cur.fetchall()}')
    cur.execute("SELECT * FROM warehouses")
    lines.append(f'  warehouses: {cur.fetchall()}')

conn.close()

# 3) 扫描其他库是否有 _backup_ 残留（确保没污染）
lines.append('')
lines.append('[3] 其他库是否有 _backup_ 残留：')
conn2 = pymysql.connect(
    host=os.getenv('MYSQL_HOST'), port=int(os.getenv('MYSQL_PORT')),
    user=os.getenv('MYSQL_USER'), password=os.getenv('MYSQL_PASSWORD'),
    charset='utf8mb4',
)
with conn2.cursor() as cur:
    cur.execute("SHOW DATABASES")
    for (db,) in cur.fetchall():
        if db in ('information_schema', 'mysql', 'performance_schema', 'sys', 'inventory_db'):
            continue
        cur.execute(f"USE `{db}`")
        cur.execute("SHOW TABLES")
        for (t,) in cur.fetchall():
            if '_backup_' in t.lower():
                cur.execute(f"SELECT COUNT(*) FROM `{t}`")
                n = cur.fetchone()[0]
                lines.append(f'  ⚠️ {db}.{t} ({n} 行)')
    lines.append('  其他库无 _backup_ 残留（除 inventory_db）')
conn2.close()

text = '\n'.join(lines)
Path(r'd:\yuan\db_inventory.txt').write_text(text, encoding='utf-8')
print(text)
