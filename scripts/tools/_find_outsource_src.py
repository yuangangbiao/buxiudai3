"""查 5001 端外协源表"""
import pymysql
CONN = dict(host='127.0.0.1', port=3306, user='root', password='88888888', connect_timeout=5, cursorclass=pymysql.cursors.DictCursor)
conn = pymysql.connect(database='steel_belt', **CONN)
cur = conn.cursor()

# 查 production_orders (外协可能存在这里)
cur.execute("DESCRIBE production_orders")
print("=== steel_belt.production_orders ===")
for r in cur.fetchall(): print(f"  {r['Field']:25s} {r['Type']}")
cur.execute("SELECT * FROM production_orders LIMIT 3")
print('\n数据:')
for r in cur.fetchall(): print(' ', dict(r))
conn.close()

# 查 supplier 相关表
print('\n=== 查所有含 out 字段的表 ===')
conn = pymysql.connect(database='steel_belt', **CONN)
cur = conn.cursor()
cur.execute("SHOW TABLES")
tables = [r[0] for r in cur.fetchall()]
for tbl in tables:
    try:
        cur.execute(f"DESCRIBE `{tbl}`")
        cols = [r['Field'] for r in cur.fetchall()]
        if any('outsource' in c.lower() or 'external' in c.lower() or 'supplier' in c.lower() for c in cols):
            print(f'  {tbl}: 含外协/供应商字段')
    except: pass
conn.close()
