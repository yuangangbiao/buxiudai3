import sqlite3, json, uuid
from datetime import datetime

db_path = 'd:/yuan/不锈钢网带跟单3.0/mobile_api_ai/wechat_container.db'
db = sqlite3.connect(db_path)
cur = db.cursor()

# 重建 WO-202605005 的 process_record
now = datetime.now().isoformat()
record_id = str(uuid.uuid4())

sql = '''INSERT INTO process_records 
(id, process_type, order_no, order_no, product_name, quantity, unit, 
 customer_name, status, current_step, steps, source, flow_type, created_at, updated_at)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''

steps = json.dumps([
    "包装入库", "原材料准备", "安装链条", "整形校直", "编制右旋", 
    "编制左旋", "焊接输送带", "表面处理", "质量检验", "输送带组装穿杆"
], ensure_ascii=False)

cur.execute(sql, (
    record_id, 'production', 'WO-202605005', 'ORD-202604210003',
    '冷冻螺旋网', 1000, '件', '客户', 'created', 0,
    steps, 'manual', 'production', now, now
))
db.commit()

# 验证
cur.execute('SELECT order_no, order_no, product_name, quantity FROM process_records')
print('=== process_records 重建后 ===')
for r in cur.fetchall():
    print(f'  {r[0]} | {r[1]} | {r[2]} | {r[3]}')

db.close()
print('\nWO-202605005 已重建到 process_records')
