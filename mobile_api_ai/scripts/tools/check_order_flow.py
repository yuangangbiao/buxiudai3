#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""查工单 ORD-202604290001 的数据流向"""
import sqlite3, json, sys

DB = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'
ORDER = sys.argv[1] if len(sys.argv) > 1 else 'ORD-202604290001'

db = sqlite3.connect(DB)
db.row_factory = sqlite3.Row
c = db.cursor()

# 1. process_records 主记录
c.execute('SELECT * FROM process_records WHERE order_no = ?', (ORDER,))
proc = c.fetchone()
if proc:
    d = dict(proc)
    print('=== 1. process_records 主记录 ===')
    for k, v in d.items():
        if k == 'steps':
            steps = json.loads(v) if isinstance(v, str) else v
            print(f'  steps ({len(steps)}个工序):')
            for i, s in enumerate(steps):
                name = s.get('name', s) if isinstance(s, dict) else s
                print(f'    [{i}] {name}')
        else:
            print(f'  {k}: {v}')
else:
    print('process_records 未找到')
print()

# 2. process_sub_steps 报工明细
c.execute('SELECT * FROM process_sub_steps WHERE order_no = ? ORDER BY created_at', (ORDER,))
rows = c.fetchall()
print(f'=== 2. process_sub_steps 报工明细 (共{len(rows)}条) ===')
if rows:
    for r in rows:
        d = dict(r)
        print(f'  [{d["created_at"]}] step={d["step_name"]} qty={d["quantity"]} operator={d["operator"]} batch={d["batch_no"]}')
else:
    print('  无报工记录')

# 3. 按 step_name 汇总
proc_id = proc['id'] if proc else ''
if proc_id:
    c.execute('SELECT step_name, SUM(quantity) as total FROM process_sub_steps WHERE process_id = ? GROUP BY step_name', (proc_id,))
    rows2 = c.fetchall()
    print(f'\n=== 3. 按工序汇总 ===')
    for r in rows2:
        print(f'  {r["step_name"]}: {r["total"]}')

db.close()

# 4. API 数据比对
print(f'\n=== 4. API 返回 vs 数据库 ===')
import urllib.request
try:
    resp = urllib.request.urlopen(f'http://127.0.0.1:5008/api/scan-info?code={ORDER}', timeout=5)
    api_data = json.loads(resp.read())['data']
    print(f'API: total_completed_qty={api_data["total_completed_qty"]}')
    for p in api_data['processes']:
        print(f'  {p["step_name"]:<16} {p["completed_qty"]}/{p["required_qty"]}')
except Exception as e:
    print(f'API 查询失败: {e}')
