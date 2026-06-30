"""补同步 process_* 表 (保留 id)"""
import pymysql

CONN = dict(host='127.0.0.1', port=3306, user='root', password='88888888', connect_timeout=10, cursorclass=pymysql.cursors.DictCursor)
conn_s = pymysql.connect(database='steel_belt', **CONN)
conn_c = pymysql.connect(database='container_center', **CONN)
cur_s = conn_s.cursor()
cur_c = conn_c.cursor()

for src, tgt, sf in [
    ('process_sub_steps', 'process_sub_steps', 'updated_at'),
    ('process_records', 'process_records', 'updated_at'),
    ('production_orders', 'production_orders', 'updated_at'),
]:
    cur_s.execute(f"DESCRIBE {src}")
    src_cols = {r['Field'] for r in cur_s.fetchall()}
    cur_c.execute(f"DESCRIBE {tgt}")
    tgt_cols = {r['Field'] for r in cur_c.fetchall()}
    common = sorted(src_cols & tgt_cols)
    if not common:
        print(f'{src}→{tgt} 共有列为空')
        continue
    # 选主键: order_no > id > 第一列
    if 'order_no' in common:
        pk = 'order_no'
    elif 'id' in common:
        pk = 'id'
    else:
        pk = common[0]
    cl = ', '.join(common)
    up = ', '.join([f"{c}=VALUES({c})" for c in common if c != pk])
    sql = f"INSERT INTO container_center.{tgt} ({cl}) SELECT {cl} FROM steel_belt.{src} ON DUPLICATE KEY UPDATE {up}"
    try:
        cur_c.execute(sql)
        n = cur_c.rowcount
        conn_c.commit()
        cur_s.execute(f'SELECT COUNT(*) c FROM {src}')
        src_n = cur_s.fetchone()['c']
        cur_c.execute(f'SELECT COUNT(*) c FROM {tgt}')
        tgt_n = cur_c.fetchone()['c']
        print(f'{src}→{tgt}: 影响 {n} 行 | src={src_n} tgt={tgt_n}')
    except Exception as e:
        print(f'{src}→{tgt} 失败: {e}')

# 验证
print()
print('=== 最终同步结果 ===')
for db, tbl in [('steel_belt','orders'), ('container_center','orders'),
                ('steel_belt','process_sub_steps'), ('container_center','process_sub_steps'),
                ('steel_belt','process_records'), ('container_center','process_records'),
                ('steel_belt','production_orders'), ('container_center','production_orders'),
                ('steel_belt','material_records'), ('container_center','material_records'),
                ('steel_belt','outsource_records'), ('container_center','outsource_records'),
                ('steel_belt','repair_records'), ('container_center','repair_records')]:
    try:
        conn = pymysql.connect(database=db, **CONN)
        cur = conn.cursor()
        cur.execute(f'SELECT COUNT(*) c FROM {tbl}')
        print(f'  {db}.{tbl:25s} {cur.fetchone()["c"]}')
        conn.close()
    except Exception as e:
        print(f'  {db}.{tbl}: {e}')

conn_s.close()
conn_c.close()
