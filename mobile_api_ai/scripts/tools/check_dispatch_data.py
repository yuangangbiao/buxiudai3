"""检查调度中心与报工系统的数据差异"""
import urllib.request
import json
import sqlite3

order_no = 'ORD-202604290001'

# 0. 获取 process_id
cc = sqlite3.connect(r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db')
cc.row_factory = sqlite3.Row
cur = cc.cursor()
cur.execute("SELECT id FROM process_records WHERE order_no = ?", (order_no,))
proc = cur.fetchone()
proc_id = proc['id'] if proc else None
print(f'容器中心 process_id: {proc_id}')

# 查看 GROUP BY 结果
if proc_id:
    cur.execute("SELECT step_name, SUM(quantity) as total FROM process_sub_steps WHERE process_id = ? GROUP BY step_name", (proc_id,))
    print('process_sub_steps GROUP BY:')
    for r in cur.fetchall():
        d = dict(r)
        print(f'  "{d["step_name"]}" -> {d["total"]}')
cc.close()

# 1. 报工系统 API (5008) - 已修复
print(f'\n=== 报工系统 API (5008) - 已修复 ===')
resp = urllib.request.urlopen(f'http://localhost:5008/api/scan-info?code={order_no}')
info = json.loads(resp.read().decode('utf-8'))
data = info.get('data', {})
print(f'总数量={data.get("quantity")} 总完成量={data.get("total_completed_qty")}')
for p in data.get('processes', []):
    if p['completed_qty'] > 0:
        print(f'  {p["step_name"]:<20} {p["completed_qty"]}/{p["required_qty"]}')

# 2. 调度中心流程列表 (5003)
print(f'\n=== 调度中心 processes (5003) ===')
try:
    resp2 = urllib.request.urlopen('http://localhost:5003/processes')
    plist = json.loads(resp2.read().decode('utf-8'))
    processes = plist.get('data', [])
    target = [p for p in processes if p.get('order_no') == order_no or p.get('order_no') == order_no]
    if target:
        p = target[0]
        print(f'订单号: {p.get("order_no")} / {p.get("order_no")}')
        print(f'状态: {p.get("status")}')
        print(f'进度: current_step={p.get("current_step")} steps={len(p.get("steps", []) or [])}')
        print(f'数量: {p.get("quantity")}')
        print(f'产品: {p.get("product_name")}')
        print(f'已用: {json.dumps(p, ensure_ascii=False)[:500]}')
    else:
        print('未找到')
except Exception as e:
    print(f'error: {e}')
