"""手动全量补同步（绕开 24h 限制）"""
import sys, os, time
sys.path.insert(0, r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai')
os.chdir(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai')
from dotenv import load_dotenv
load_dotenv(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\.env')
import logging
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')

# patch 回溯窗口 24h -> 3650 天
import etl_local_mirror
etl_local_mirror._run_etl_cycle_orig = etl_local_mirror._run_etl_cycle

import pymysql
from datetime import datetime, timedelta
from etl_local_mirror import _sync_state, _sync_table

CONN = dict(host='127.0.0.1', port=3306, user='root', password='88888888', connect_timeout=5, cursorclass=pymysql.cursors.DictCursor)

def full_sync_table(src, tgt, sf):
    """全量同步一张表, 每次 200 行, 翻页直到同步完"""
    last_time = '1000-01-01 00:00:00'
    total = 0
    while True:
        n = _sync_table(
            source_table=src, target_table=tgt,
            sync_field=sf, batch_size=200, last_sync_time=last_time
        )
        total += n
        if n < 200:
            break
        # 翻页
        conn = pymysql.connect(database='steel_belt', **CONN)
        cur = conn.cursor()
        cur.execute(f"SELECT MAX({sf}) m FROM {src}")
        m = cur.fetchone()['m']
        conn.close()
        if not m: break
        if isinstance(m, datetime):
            last_time = m.strftime('%Y-%m-%d %H:%M:%S')
        else:
            last_time = str(m)
        if total > 10000: break
    return total

print("=== 全量补同步 (绕过 24h 限制) ===")
for src, tgt, sf in [
    ('orders', 'orders', 'updated_at'),
    ('production_orders', 'production_orders', 'updated_at'),
    ('process_records', 'process_records', 'updated_at'),
    ('violation_log', 'violations', 'created_at'),
    ('work_orders', 'work_orders', 'updated_at'),
]:
    n = full_sync_table(src, tgt, sf)
    print(f"  {src} → {tgt}: {n} 行")

print()
print("=== 同步结果 ===")
for db, tbl in [('steel_belt','orders'), ('container_center','orders'),
                ('steel_belt','process_sub_steps'), ('container_center','process_sub_steps'),
                ('steel_belt','process_records'), ('container_center','process_records')]:
    conn = pymysql.connect(database=db, **CONN)
    cur = conn.cursor()
    cur.execute(f'SELECT COUNT(*) c FROM {tbl}')
    print(f'  {db}.{tbl:25s} {cur.fetchone()["c"]}')
    conn.close()
