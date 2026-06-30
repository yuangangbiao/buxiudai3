"""查 container_center.process_sub_steps 中外协工序"""
import pymysql
CONN = dict(host='127.0.0.1', port=3306, user='root', password='88888888', connect_timeout=5, cursorclass=pymysql.cursors.DictCursor)
conn = pymysql.connect(database='container_center', **CONN)
cur = conn.cursor()

cur.execute('DESCRIBE process_sub_steps')
print("=== container_center.process_sub_steps 字段 ===")
for r in cur.fetchall(): print(f"  {r['Field']:25s} {r['Type']}")

# 找含 out 的字段
out_cols = []
cur.execute("DESCRIBE process_sub_steps")
for r in cur.fetchall():
    if 'out' in r['Field'].lower() or 'supplier' in r['Field'].lower():
        out_cols.append(r['Field'])
print(f'\n外协相关字段: {out_cols}')

if out_cols:
    for c in out_cols:
        try:
            cur.execute(f"SELECT `{c}`, COUNT(*) cnt FROM process_sub_steps GROUP BY `{c}`")
            print(f'\n=== {c} 分布 ===')
            for r in cur.fetchall(): print(f'  {r[c]}: {r["cnt"]}')
        except Exception as e:
            print(f'  {c}: ERR {e}')

# 查 is_outsource=1 的样本
cur.execute("SELECT * FROM process_sub_steps WHERE is_outsource=1 LIMIT 3")
rows = cur.fetchall()
print(f'\n=== is_outsource=1 样本 ({len(rows)} 条) ===')
for r in rows: print(' ', dict(r))
conn.close()
