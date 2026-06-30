"""直接 SQL 全量补同步 (绕过 ETL 增量逻辑)"""
import pymysql
from datetime import datetime

CONN = dict(host='127.0.0.1', port=3306, user='root', password='88888888', connect_timeout=10, cursorclass=pymysql.cursors.DictCursor)

# 检查列差异
conn_s = pymysql.connect(database='steel_belt', **CONN)
conn_c = pymysql.connect(database='container_center', **CONN)
cur_s = conn_s.cursor()
cur_c = conn_c.cursor()

cur_s.execute("DESCRIBE orders")
sb_cols = {r['Field']: r['Type'] for r in cur_s.fetchall()}
cur_c.execute("DESCRIBE orders")
cc_cols = {r['Field']: r['Type'] for r in cur_c.fetchall()}
common = sorted(set(sb_cols) & set(cc_cols))
print('共有列:', common)
print()
print('steel_belt.orders 独有:', set(sb_cols) - set(cc_cols))
print('container_center.orders 独有:', set(cc_cols) - set(sb_cols))

# 用 INSERT ... SELECT 同步（仅共有列，排除主键 id）
sync_cols = [c for c in common if c != 'id']
print(f'\n同步列 ({len(sync_cols)}):', sync_cols)

col_list = ', '.join(sync_cols)
sql = f"INSERT INTO container_center.orders ({col_list}) SELECT {col_list} FROM steel_belt.orders ON DUPLICATE KEY UPDATE "
update_parts = [f"{c}=VALUES({c})" for c in sync_cols if c != 'order_no']
sql += ', '.join(update_parts)
print('\nSQL 长度:', len(sql))
print('SQL 前 200 字符:', sql[:200])

cur_c.execute(sql)
n = cur_c.rowcount
conn_c.commit()
print(f'\n直接 SQL 同步 orders: {n} 行受影响')

# 同样同步 process_sub_steps, process_records, production_orders
for src, tgt, sf in [
    ('process_sub_steps', 'process_sub_steps', 'updated_at'),
    ('process_records', 'process_records', 'updated_at'),
    ('production_orders', 'production_orders', 'updated_at'),
]:
    cur_s.execute(f"DESCRIBE {src}")
    src_cols = {r['Field']: r['Type'] for r in cur_s.fetchall()}
    cur_c.execute(f"DESCRIBE {tgt}")
    tgt_cols = {r['Field']: r['Type'] for r in cur_c.fetchall()}
    common = sorted(set(src_cols) & set(tgt_cols))
    if 'id' in common:
        common.remove('id')
    if not common:
        print(f'{src}→{tgt} 共有列为空, 跳过')
        continue
    cl = ', '.join(common)
    pk = 'order_no' if 'order_no' in common else common[0]
    up = ', '.join([f"{c}=VALUES({c})" for c in common if c != pk])
    sql = f"INSERT INTO container_center.{tgt} ({cl}) SELECT {cl} FROM steel_belt.{src} ON DUPLICATE KEY UPDATE {up}"
    try:
        cur_c.execute(sql)
        n = cur_c.rowcount
        conn_c.commit()
        print(f'{src}→{tgt}: {n} 行')
    except Exception as e:
        print(f'{src}→{tgt} 失败: {e}')

# 检查结果
print()
print('=== 同步结果 ===')
for db, tbl in [('steel_belt','orders'), ('container_center','orders'),
                ('steel_belt','process_sub_steps'), ('container_center','process_sub_steps'),
                ('steel_belt','process_records'), ('container_center','process_records'),
                ('steel_belt','production_orders'), ('container_center','production_orders')]:
    conn = pymysql.connect(database=db, **CONN)
    cur = conn.cursor()
    cur.execute(f'SELECT COUNT(*) c FROM {tbl}')
    print(f'  {db}.{tbl:25s} {cur.fetchone()["c"]}')
    conn.close()

conn_s.close()
conn_c.close()
