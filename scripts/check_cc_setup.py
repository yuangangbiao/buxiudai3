import pymysql

conn = pymysql.connect(host='localhost', user='root', password='88888888', database='container_center', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
c = conn.cursor()

# data_packages 表结构
c.execute('SHOW COLUMNS FROM data_packages')
print('=== data_packages 表结构 ===')
for col in c.fetchall():
    f = col['Field']
    t = col['Type']
    e = col.get('Extra', '')
    print(f'  {f:30s} {t:30s} {e or ""}')

# 查询一些操作员
c.execute('SELECT id, name, role FROM workers LIMIT 10')
rows = c.fetchall()
print(f'\n=== workers 表 (前10) ===')
for r in rows:
    print(f'  id={r["id"]} name={r["name"]} role={r["role"]}')

# 检查 quality_records 和 material_records 表是否存在
for tbl in ['quality_records', 'material_records', 'outsource_records', 'repair_records']:
    c.execute(f'SELECT COUNT(*) as cnt FROM information_schema.tables WHERE table_schema=database() AND table_name="{tbl}"')
    r = c.fetchone()
    print(f'\n表 {tbl}: {"存在" if r["cnt"] > 0 else "不存在"}')
    if r['cnt'] > 0:
        c.execute(f'SHOW COLUMNS FROM {tbl}')
        cols = c.fetchall()
        for col in cols:
            print(f'  {col["Field"]:30s} {col["Type"]:30s}')
            if len(cols) > 8:
                print(f'  ... 共 {len(cols)} 列')
                break

conn.close()
