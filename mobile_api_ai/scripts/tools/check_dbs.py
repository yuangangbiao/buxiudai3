#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""对比多个数据库文件中的工单数据"""
import sqlite3, json, os

ORDER = 'ORD-202604290001'
BASE = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai'

# [F6 T4 清理] container_storage.db 已彻底移除,不再检查
dbs = ['container_center.db', 'wechat_container.db']

for db_name in dbs:
    path = os.path.join(BASE, db_name)
    if not os.path.exists(path):
        print(f'\n=== {db_name} (文件不存在) ===')
        continue
    
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    c = db.cursor()
    
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r['name'] for r in c.fetchall()]
    
    print(f'\n=== {db_name} ===')
    print(f'  表: {tables}')
    
    if 'process_records' in tables:
        c.execute('SELECT * FROM process_records WHERE order_no = ?', (ORDER,))
        r = c.fetchone()
        if r:
            d = dict(r)
            print(f'  process_records: id={d["id"][:8]}... qty={d["quantity"]} current_step={d["current_step"]} status={d["status"]}')
            steps = json.loads(d['steps']) if isinstance(d['steps'], str) else d['steps']
            print(f'  steps: {len(steps)}')
            
            pid = d['id']
            c.execute('SELECT COUNT(*) as cnt FROM process_sub_steps WHERE process_id = ?', (pid,))
            cnt = c.fetchone()['cnt']
            print(f'  sub_steps: {cnt}条')
            
            if cnt > 0:
                c.execute('SELECT step_name, SUM(quantity) as total FROM process_sub_steps WHERE process_id=? GROUP BY step_name', (pid,))
                for row in c.fetchall():
                    print(f'    {row["step_name"]}: {row["total"]}')
        else:
            print(f'  未找到工单 {ORDER}')
    
    db.close()

print('\n--- 通过 API 查询 ---')
import urllib.request
try:
    resp = urllib.request.urlopen(f'http://127.0.0.1:5008/api/scan-info?code={ORDER}', timeout=5)
    api_data = json.loads(resp.read())
    print(f'  API code={api_data.get("code")}')
    if api_data.get('code') == 0:
        d = api_data['data']
        print(f'  total_completed_qty={d["total_completed_qty"]}')
        for p in d['processes']:
            print(f'    {p["step_name"]:<16} {p["completed_qty"]}/{p["required_qty"]}')
    else:
        print(f'  API error: {api_data}')
except Exception as e:
    print(f'  API 查询失败: {e}')
