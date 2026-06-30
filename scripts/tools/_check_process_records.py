import sqlite3, json

db = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# process_records 数据量
cur.execute('SELECT COUNT(*) FROM process_records')
cnt = cur.fetchone()[0]
print(f'process_records 总记录: {cnt}条')

# 看结构和样例
cur.execute('PRAGMA table_info(process_records)')
cols = cur.fetchall()
print(f'\nprocess_records 列 ({len(cols)}列):')
for c in cols:
    print(f'  {c[1]} ({c[2]})')

# 前3条样例
cur.execute('SELECT id, order_no, work_order_no, product_name, quantity, status, current_step FROM process_records LIMIT 3')
rows = cur.fetchall()
print(f'\n前3条样例:')
for r in rows:
    print(f'  id={str(r[0])[:12]}... order_no={r[1]} work_order_no={r[2]} product={r[3]} qty={r[4]} status={r[5]} step={r[6]}')

# steps 的内容
cur.execute('SELECT id, work_order_no, steps FROM process_records LIMIT 1')
r = cur.fetchone()
if r:
    steps = r[2]
    if isinstance(steps, str):
        try:
            steps_list = json.loads(steps)
            print(f'\nsteps 样例: {len(steps_list)} 个步骤')
            for s in steps_list[:3]:
                print(f'  {s}')
        except:
            print(f'steps 解析失败: {steps[:100]}')

# data_packages 对比
cur.execute('SELECT COUNT(*) FROM data_packages')
dp_cnt = cur.fetchone()[0]
cur.execute('SELECT COUNT(*) FROM data_packages WHERE data_type IN (?, ?)', ('report', 'process'))
dp_task_cnt = cur.fetchone()[0]
print(f'\ndata_packages 总记录: {dp_cnt}条')
print(f'data_packages report/process: {dp_task_cnt}条')

conn.close()
