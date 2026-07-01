import sqlite3
import json
import os

db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'wechat_container.db')
if not os.path.exists(db_path):
    print(f'数据库文件不存在: {db_path}')
    exit(1)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# 列出所有不同的data_type
cur.execute('SELECT DISTINCT data_type FROM data_packages')
types = cur.fetchall()
print('=== 所有data_type类型 ===')
for t in types:
    print(f'  {t[0]}')

# 列出所有 work_order 类型记录
print()
print('=== data_type=work_order 记录 ===')
cur.execute("SELECT id, data_type, title, status, content, related_order, source, created_at FROM data_packages WHERE data_type='work_order' ORDER BY created_at DESC LIMIT 20")
rows = cur.fetchall()
print(f'共 {len(rows)} 条')
for r in rows:
    content_str = r[4] or '{}'
    try:
        content = json.loads(content_str) if isinstance(content_str, str) else content_str
    except Exception:
        content = {}
    pn = content.get('product_name', '')
    qty = content.get('quantity', 0)
    order_no = content.get('order_no', r[5] or '')
    print(f'  ID={str(r[0])[:8]:8s} | title={str(r[2])[:30]:30s} | order={str(order_no):20s} | product={str(pn):15s} | qty={str(qty):6s} | status={str(r[3]):12s}')

# 列出所有 非report 记录
print()
print("=== 所有 data_type != 'report' 记录 ===")
cur.execute("SELECT id, data_type, title, status, content, related_order, source, created_at FROM data_packages WHERE data_type!='report' ORDER BY created_at DESC")
rows = cur.fetchall()
print(f'共 {len(rows)} 条')
for r in rows:
    content_str = r[4] or '{}'
    try:
        content = json.loads(content_str) if isinstance(content_str, str) else content_str
    except Exception:
        content = {}
    pn = content.get('product_name', '')
    qty = content.get('quantity', 0)
    order_no = content.get('order_no', r[5] or '')
    print(f'  ID={str(r[0])[:8]:8s} | type={str(r[1]):12s} | title={str(r[2])[:30]:30s} | order={str(order_no):20s} | product={str(pn):15s} | qty={str(qty):6s} | src={str(r[6]):16s} | status={str(r[3]):12s}')

# 列出 process_records 表（如果有）
print()
print('=== process_records 表 ===')
try:
    cur.execute("SELECT id, order_no, product_name, quantity, status, current_step, flow_type, created_at FROM process_records ORDER BY created_at DESC LIMIT 20")
    rows = cur.fetchall()
    if rows:
        print(f'共 {len(rows)} 条')
        for r in rows:
            print(f'  ID={str(r[0])[:8]:8s} | order={str(r[1]):20s} | product={str(r[2]):15s} | qty={str(r[3]):6s} | status={str(r[4]):12s} | step={str(r[5]):4s} | type={str(r[6]):12s}')
    else:
        print('  表为空')
except Exception as e:
    print(f'  表不存在: {e}')

conn.close()
