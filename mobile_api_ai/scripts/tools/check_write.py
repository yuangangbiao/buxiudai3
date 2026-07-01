#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""验证报工数据写入的数据库"""
import sqlite3, os

BASE = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai'
ORDER = 'ORD-202604290001'
PID = 'f44f2f00-5629-4d5c-9b91-77457294781e'

dbs_to_check = {
    'wechat_container.db': ['process_records', 'process_sub_steps'],
    'container_center.db': ['process_records', 'process_sub_steps'],
    'mobile_wechat.db': ['orders', 'sub_steps'],
}

for db_name, tables in dbs_to_check.items():
    path = os.path.join(BASE, db_name)
    if not os.path.exists(path):
        print(f'\n=== {db_name} (不存在) ===')
        continue
    
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    c = db.cursor()
    
    print(f'\n=== {db_name} ===')
    
    for table in tables:
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        if not c.fetchone():
            print(f'  表 {table}: 不存在')
            continue
        
        if table == 'process_sub_steps':
            c.execute('SELECT * FROM process_sub_steps WHERE process_id=? ORDER BY created_at DESC LIMIT 3', (PID,))
            rows = c.fetchall()
            if rows:
                print(f'  process_sub_steps (按process_id, 最新3条):')
                for r in rows:
                    d = dict(r)
                    print(f'    [{d["created_at"]}] step="{d["step_name"]}" qty={d["quantity"]} op={d["operator"]}')
            else:
                print(f'  process_sub_steps: 无记录(process_id={PID})')
        
        if table in ['process_records']:
            c.execute(f"SELECT id, order_no, quantity, current_step, status FROM {table} WHERE order_no=?", (ORDER,))
            r = c.fetchone()
            if r:
                print(f'  process_records: id={r["id"][:8]}... qty={r["quantity"]} step={r["current_step"]} status={r["status"]}')
            else:
                print(f'  process_records: 未找到 {ORDER}')
        
        if table == 'orders':
            c.execute(f"SELECT * FROM orders WHERE order_id=? OR order_no=?", (ORDER, ORDER))
            r = c.fetchone()
            print(f'  orders: {"找到" if r else "未找到"}')
        
        if table == 'sub_steps':
            c.execute('SELECT * FROM sub_steps WHERE order_no=? ORDER BY created_at DESC LIMIT 3', (ORDER,))
            rows = c.fetchall()
            if rows:
                print(f'  sub_steps (最新3条):')
                for r in rows:
                    d = dict(r)
                    print(f'    [{d["created_at"]}] step="{d.get("step_name","")}" qty={d.get("quantity",0)} op={d.get("operator","")}')
            else:
                print(f'  sub_steps: 无记录')
    
    db.close()
