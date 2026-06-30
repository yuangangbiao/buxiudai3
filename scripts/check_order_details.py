# -*- coding: utf-8 -*-
"""检查可测试数据"""
import pymysql

STEEL_CONFIG = {'host':'localhost','user':'root','password':'88888888',
    'database':'steel_belt','charset':'utf8mb4','cursorclass':pymysql.cursors.DictCursor}

conn = pymysql.connect(**STEEL_CONFIG)
try:
    with conn.cursor() as c:
        c.execute("SELECT id, order_no FROM production_orders WHERE order_no='ORD-202604210002'")
        po = c.fetchone()
        print(f'production_orders: id={po["id"]}, order_no={po["order_no"]}')

        c.execute("SELECT id, production_id, process_name, process_code, planned_qty, completed_qty, status, flow_type, process_seq, unit FROM process_records WHERE order_no='ORD-202604210002' ORDER BY process_seq")
        rows = c.fetchall()
        for r in rows:
            diff = r['planned_qty'] - r['completed_qty']
            print(f"  id={r['id']} prod_id={r['production_id']} seq={r['process_seq']} {r['process_name']}({r['process_code']}) 计划={r['planned_qty']} 完成={r['completed_qty']} 差={diff} 状态={r['status']} flow={r['flow_type']}")
finally:
    conn.close()
