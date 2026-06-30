"""查 process_sub_steps 中外协工序"""
import pymysql
CONN = dict(host='127.0.0.1', port=3306, user='root', password='88888888', connect_timeout=5, cursorclass=pymysql.cursors.DictCursor)
conn = pymysql.connect(database='steel_belt', **CONN)
cur = conn.cursor()
cur.execute("SELECT is_outsource, COUNT(*) c FROM process_sub_steps GROUP BY is_outsource")
print('=== process_sub_steps.is_outsource 分布 ===')
for r in cur.fetchall(): print(f'  {r["is_outsource"]}: {r["c"]}')
cur.execute("SELECT * FROM process_sub_steps WHERE is_outsource=1 LIMIT 3")
print('\n=== 外协工序样本 ===')
for r in cur.fetchall(): print(' ', dict(r))
conn.close()
