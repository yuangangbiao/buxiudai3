#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""深入查 wechat_container.db 实际数据"""
import sqlite3, json, os

BASE = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai'
DB = os.path.join(BASE, 'wechat_container.db')
ORDER = 'ORD-202604290001'

db = sqlite3.connect(DB)
db.row_factory = sqlite3.Row
c = db.cursor()

# 1. 查所有 process_records
c.execute("SELECT id, order_no, quantity, current_step, status, steps FROM process_records WHERE order_no = ?", (ORDER,))
r = c.fetchone()
if r:
    d = dict(r)
    pid = d['id']
    print(f'process_id: {pid}')
    print(f'quantity: {d["quantity"]}, current_step: {d["current_step"]}, status: {d["status"]}')
else:
    print(f'process_records 未找到 {ORDER}')
    # 搜索所有记录
    c.execute("SELECT id, order_no, order_no FROM process_records LIMIT 5")
    for r in c.fetchall():
        print(f'  其他记录: {dict(r)}')
    db.close()
    exit()

# 2. 查 process_sub_steps — 用 process_id 查全部
c.execute('SELECT * FROM process_sub_steps WHERE process_id = ? ORDER BY created_at', (pid,))
all_ss = c.fetchall()
print(f'\n=== process_sub_steps 全部(按 process_id={pid}) === 共{len(all_ss)}条')
for ss in all_ss:
    d = dict(ss)
    print(f'  [{d["created_at"]}] step="{d["step_name"]}" qty={d["quantity"]} op={d["operator"]} batch={d["batch_no"]}')

# 3. 按原始 step_name 汇总
print('\n=== 按原始 step_name 汇总 ===')
c.execute('SELECT step_name, SUM(quantity) as total FROM process_sub_steps WHERE process_id=? GROUP BY step_name', (pid,))
for r in c.fetchall():
    print(f'  "{r["step_name"]}": {r["total"]}')

# 4. 同样查 order_no 方式
c.execute('SELECT * FROM process_sub_steps WHERE order_no = ? ORDER BY created_at', (ORDER,))
by_order = c.fetchall()
print(f'\n=== process_sub_steps (按 order_no) === 共{len(by_order)}条')
for ss in by_order:
    d = dict(ss)
    print(f'  [{d["created_at"]}] step="{d["step_name"]}" qty={d["quantity"]} op={d["operator"]} batch={d["batch_no"]}')

# 5. 检查是否有其他 process_id 也关联此 ORDER
c.execute("SELECT id, quantity, current_step FROM process_records WHERE order_no = ?", (ORDER,))
others = c.fetchall()
print(f'\n=== 同 order_no 的其他 process_records === {len(others)}条')
for r in others:
    print(f'  id={r["id"]} qty={r["quantity"]} current_step={r["current_step"]}')

db.close()

# 6. API 查询
print('\n=== API 实时查询 ===')
import urllib.request
try:
    resp = urllib.request.urlopen(f'http://127.0.0.1:5008/api/scan-info?code={ORDER}', timeout=5)
    data = json.loads(resp.read())
    if data.get('code') == 0:
        d = data['data']
        print(f'总完成: {d["total_completed_qty"]}')
        for p in d['processes']:
            print(f'  {p["step_name"]}: {p["completed_qty"]}/{p["required_qty"]} (last: {p["last_report_operator"]} qty={p["last_report_qty"]})')
    else:
        print(f'API 错误: {data}')
except Exception as e:
    print(f'API 失败: {e}')
