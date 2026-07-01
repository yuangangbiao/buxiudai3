#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查 d:\yuan\wechat_container.db（API 实际使用的数据库）"""
import sqlite3, json

ROOT_DB = r'D:\yuan\wechat_container.db'
SUB_DB = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'

for label, path in [('API 实际使用(d:\\yuan\\)', ROOT_DB), ('项目目录内', SUB_DB)]:
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    c = db.cursor()
    
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r['name'] for r in c.fetchall()]
    print(f'=== {label}: {path} ===')
    print(f'  表: {tables}')
    
    if 'process_records' in tables:
        c.execute('SELECT id, order_no, quantity, current_step, status FROM process_records')
        rows = c.fetchall()
        print(f'  process_records: {len(rows)}条')
        for r in rows:
            pid = r['id'][:8] if r['id'] else 'N/A'
            print(f'    {pid}... {r["order_no"]} qty={r["quantity"]} step={r["current_step"]} status={r["status"]}')
    
    if 'process_sub_steps' in tables:
        c.execute('SELECT COUNT(*) as cnt FROM process_sub_steps')
        cnt = c.fetchone()['cnt']
        print(f'  process_sub_steps: {cnt}条')
        if cnt > 0:
            c.execute('SELECT step_name, quantity, operator, created_at FROM process_sub_steps ORDER BY created_at DESC LIMIT 5')
            for r in c.fetchall():
                print(f'    [{r["created_at"]}] {r["step_name"]} qty={r["quantity"]} op={r["operator"]}')
    
    db.close()
    print()

# API 实时查
import urllib.request
print('=== API 实时查询 ===')
resp = urllib.request.urlopen('http://127.0.0.1:5008/api/scan-info?code=ORD-202604290001', timeout=5)
data = json.loads(resp.read())
if data.get('code') == 0:
    d = data['data']
    print(f'  total_completed_qty={d["total_completed_qty"]}')
    for p in d['processes']:
        print(f'  {p["step_name"]}: {p["completed_qty"]}/{p["required_qty"]}')
else:
    print(f'  API: {data}')
