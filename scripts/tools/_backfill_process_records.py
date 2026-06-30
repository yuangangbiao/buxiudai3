"""从 process_sub_steps + production_orders 补 process_records 缺失记录"""
import pymysql
from datetime import datetime

CONN = dict(host='127.0.0.1', port=3306, user='root', password='88888888', connect_timeout=10, cursorclass=pymysql.cursors.DictCursor)
conn = pymysql.connect(database='container_center', **CONN)
cur = conn.cursor()

# 1. 找有 process_sub_steps 但无 process_records 的 order_no
cur.execute("""
    SELECT DISTINCT pss.order_no
    FROM process_sub_steps pss
    LEFT JOIN process_records pr ON pr.order_no COLLATE utf8mb4_unicode_ci = pss.order_no COLLATE utf8mb4_unicode_ci
    WHERE pr.order_no IS NULL
      AND pss.order_no IS NOT NULL AND pss.order_no != ''
""")
missing = [r['order_no'] for r in cur.fetchall()]
print(f'缺失 process_records 的 order_no: {len(missing)} 条')
for o in missing[:10]: print(f'  {o}')

# 2. 查 process_sub_steps 的字段结构
cur.execute('DESCRIBE process_sub_steps')
ss_cols = {r['Field'] for r in cur.fetchall()}
print(f'\nprocess_sub_steps 字段: {sorted(ss_cols)[:15]}...')

# 3. 查 process_records 字段
cur.execute('DESCRIBE process_records')
pr_cols = {r['Field']: r for r in cur.fetchall()}
print(f'\nprocess_records 字段: {sorted(pr_cols.keys())[:20]}...')

# 4. 从 process_sub_steps 聚合插入
# 通用字段映射: order_no, process_code, step_name, process_name, product_name, quantity, status
sync_count = 0
for order_no in missing:
    cur.execute("SELECT * FROM process_sub_steps WHERE order_no=%s ORDER BY id LIMIT 1", (order_no,))
    ss = cur.fetchone()
    if not ss: continue

    # 聚合工序列表
    cur.execute("SELECT step_name, process_code, quantity, completed_qty, status FROM process_sub_steps WHERE order_no=%s", (order_no,))
    sub_steps = cur.fetchall()
    steps_json = None
    import json
    if sub_steps:
        steps_list = []
        for s in sub_steps:
            steps_list.append({
                'name': s.get('step_name', ''),
                'process_code': s.get('process_code', ''),
                'quantity': float(s.get('quantity', 0) or 0),
                'status': s.get('status', 'pending'),
            })
        steps_json = json.dumps(steps_list, ensure_ascii=False)

    # 从 production_orders 取订单信息
    cur.execute("SELECT * FROM production_orders WHERE order_no=%s LIMIT 1", (order_no,))
    po = cur.fetchone() or {}
    # 从 orders 表取
    cur.execute("SELECT * FROM orders WHERE order_no=%s LIMIT 1", (order_no,))
    o = cur.fetchone() or {}

    # 构造 process_records
    rec = {
        'id': f'PR-{order_no}',
        'process_type': 'production',
        'process_code': ss.get('process_code', 'UNKNOWN'),
        'process_name': ss.get('step_name', '未命名工序'),
        'order_no': order_no,
        'product_name': o.get('product_name', ''),
        'quantity': float(ss.get('quantity', 0) or 0),
        'customer_name': o.get('customer_name', ''),
        'status': 'pending',
        'current_step': 0,
        'step_name': ss.get('step_name', ''),
        'steps': steps_json,
        'flow_type': 'production',
        'is_archived': int(o.get('is_archived', 0) or 0),
        'is_deleted': 0,
    }

    # 只插入 process_records 实际存在的列
    cols_avail = set(pr_cols.keys())
    rec_filtered = {k: v for k, v in rec.items() if k in cols_avail and v is not None}
    if not rec_filtered: continue

    cl = ', '.join(rec_filtered.keys())
    ph = ', '.join(['%s'] * len(rec_filtered))
    try:
        cur.execute(
            f"INSERT INTO process_records ({cl}) VALUES ({ph})",
            tuple(rec_filtered.values())
        )
        sync_count += 1
    except Exception as e:
        print(f'  {order_no} 插入失败: {e}')

conn.commit()
print(f'\n补同步 process_records: {sync_count} 条')

# 5. 验证
cur.execute("SELECT COUNT(*) c FROM process_records")
print(f'当前 process_records 总数: {cur.fetchone()["c"]}')

conn.close()
