"""测试 ORD-202604290001 报工 - 追踪每一步"""
import urllib.request
import json
import sqlite3
import sys

BASE = 'http://localhost:5008'

def get(path):
    url = BASE + path
    resp = urllib.request.urlopen(url)
    return json.loads(resp.read().decode('utf-8'))

def post(path, data):
    body = json.dumps(data, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(BASE + path, data=body,
                                 headers={'Content-Type': 'application/json'})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read().decode('utf-8'))

CC_PATH = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'
CS_PATH = 'D:\\yuan\\不锈钢网带跟单3.0\\mobile_api_ai\\chengsheng.db'

def query_cc(sql, params=()):
    conn = sqlite3.connect(CC_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def query_cs(sql, params=()):
    conn = sqlite3.connect(CS_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# 1. 查工序列表
print('=== 1. 订单工序列表 (API) ===')
info = get('/api/scan-info?code=ORD-202604290001')
data = info.get('data', {})
print(f'订单数量: {data.get("quantity")}')
print(f'总完成量: {data.get("total_completed_qty")}')
print(f'工序列表:')
for p in data.get('processes', []):
    print(f'  [pid={p["process_id"][:8]}] {p["step_name"]}: {p["completed_qty"]}/{p["required_qty"]}')

# 2. 容器中心该订单的所有报工记录
print(f'\n=== 2. 容器中心 process_sub_steps 表 ===')
rows = query_cc("SELECT * FROM process_sub_steps WHERE order_no = 'ORD-202604290001' ORDER BY rowid DESC")
print(f'记录数: {len(rows)}')
for row in rows:
    print(f'  step="{row["step_name"]}" qty={row["quantity"]} pid={str(row.get("process_id",""))[:8]} time={str(row.get("created_at",""))[:19]}')

# 3. 查看容器中心 process_records 表中该订单的记录
print(f'\n=== 3. 容器中心 process_records 表 ===')
proc_rows = query_cc("SELECT id, product_name, order_no, quantity, steps FROM process_records WHERE order_no = 'ORD-202604290001' ORDER BY rowid")
for row in proc_rows:
    print(f'  id={row["id"][:16]} product="{row["product_name"]}" order_no={row["order_no"]} qty={row["quantity"]}')

# 4. chengsheng.db 中该订单的报工记录
print(f'\n=== 4. chengsheng.db sub_steps 表 ===')
cs_rows = query_cs("SELECT * FROM sub_steps WHERE order_no = 'ORD-202604290001' ORDER BY id DESC")
print(f'记录数: {len(cs_rows)}')
for row in cs_rows:
    print(f'  id={row["id"]} step="{row["step_name"]}" qty={row["quantity"]} pid={str(row.get("process_id",""))[:8]}')

# 5. 测试提交一次报工
print(f'\n=== 5. 测试提交报工 ===')
test_data = {
    'process_id': data['processes'][0]['process_id'],
    'order_no': 'ORD-202604290001',
    'step_name': data['processes'][0]['step_name'],
    'quantity': 10,
    'operator': '测试脚本',
    'remark': '脚本测试提交'
}
print(f'提交参数: process_id={test_data["process_id"][:16]} step_name="{test_data["step_name"]}" qty={test_data["quantity"]}')
resp = post('/api/process_sub_step', test_data)
print(f'返回: code={resp.get("code")} msg={resp.get("message")}')
if resp.get('code') == 0:
    rec = resp.get('data', {}).get('record', {})
    print(f'  新记录 step="{rec.get("step_name")}" qty={rec.get("quantity")}')

# 6. 再次查询验证
print(f'\n=== 6. 提交后验证 ===')
rows2 = query_cc("SELECT * FROM process_sub_steps WHERE order_no = 'ORD-202604290001' ORDER BY rowid DESC")
print(f'容器中心记录数: {len(rows2)}')
cs_rows2 = query_cs("SELECT * FROM sub_steps WHERE order_no = 'ORD-202604290001' ORDER BY id DESC")
print(f'chengsheng.db 记录数: {len(cs_rows2)}')

info2 = get('/api/scan-info?code=ORD-202604290001')
data2 = info2.get('data', {})
for p in data2.get('processes', []):
    if p['completed_qty'] > 0:
        print(f'  工序 "{p["step_name"]}": completed_qty={p["completed_qty"]}/{p["required_qty"]}')
