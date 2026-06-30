"""查 inventory_db 和桌面端 order_materials 内容"""
import pymysql

CONN = dict(host='127.0.0.1', port=3306, user='root', password='88888888', connect_timeout=5, cursorclass=pymysql.cursors.DictCursor)

# 1. 查 inventory_db
try:
    conn = pymysql.connect(database='inventory_db', **CONN)
    cur = conn.cursor()
    cur.execute("SHOW TABLES")
    tables = [list(r.values())[0] for r in cur.fetchall()]
    print(f"=== inventory_db ({len(tables)} 表) ===")
    for t in tables: print(f"  {t}")
    conn.close()
except Exception as e:
    print(f'inventory_db: ERR {e}')

# 2. 查 steel_belt.order_materials
print()
print("=== steel_belt.order_materials ===")
conn = pymysql.connect(database='steel_belt', **CONN)
cur = conn.cursor()
try:
    cur.execute("DESCRIBE order_materials")
    for r in cur.fetchall(): print(f"  {r['Field']:25s} {r['Type']}")
    cur.execute("SELECT COUNT(*) c FROM order_materials")
    print(f'\n  count: {cur.fetchone()["c"]}')
    cur.execute("SELECT * FROM order_materials LIMIT 3")
    for r in cur.fetchall(): print(' ', r)
except Exception as e:
    print(f'  ERR {e}')
conn.close()

# 3. 查 steel_belt.material_history
print()
print("=== steel_belt.material_history ===")
conn = pymysql.connect(database='steel_belt', **CONN)
cur = conn.cursor()
try:
    cur.execute("SELECT COUNT(*) c FROM material_history")
    print(f'  count: {cur.fetchone()["c"]}')
    cur.execute("SELECT * FROM material_history LIMIT 2")
    for r in cur.fetchall(): print(' ', r)
except Exception as e:
    print(f'  ERR {e}')
conn.close()

# 4. 查 container_center.material_records / outsource_records 表结构
print()
print("=== container_center.material_records 表结构 ===")
conn = pymysql.connect(database='container_center', **CONN)
cur = conn.cursor()
try:
    cur.execute("DESCRIBE material_records")
    for r in cur.fetchall(): print(f"  {r['Field']:25s} {r['Type']}")
    cur.execute("DESCRIBE outsource_records")
    print()
    print("=== container_center.outsource_records 表结构 ===")
    for r in cur.fetchall(): print(f"  {r['Field']:25s} {r['Type']}")
except Exception as e:
    print(f'  ERR {e}')
conn.close()
