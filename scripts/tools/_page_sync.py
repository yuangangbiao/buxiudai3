"""翻页同步 - 把 orders 同步到满"""
import sys, os
sys.path.insert(0, r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai')
os.chdir(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai')
from dotenv import load_dotenv
load_dotenv(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\.env')
import logging
logging.basicConfig(level=logging.ERROR)
from etl_local_mirror import _sync_table
import pymysql
from datetime import datetime, timedelta

CONN = dict(host='127.0.0.1', port=3306, user='root', password='88888888', connect_timeout=5, cursorclass=pymysql.cursors.DictCursor)

def page_sync(src, tgt, sf, page_size=200, max_iter=15):
    last_time = '1000-01-01 00:00:00'
    total = 0
    for i in range(max_iter):
        n = _sync_table(src, tgt, sf, page_size, last_time)
        total += n
        if n == 0:
            print(f'  iter {i+1}: 0 行 (无更多数据) 累计 {total}')
            break
        print(f'  iter {i+1}: 同步 {n} 行 累计 {total}')
        # 翻页
        conn = pymysql.connect(database='steel_belt', **CONN)
        cur = conn.cursor()
        cur.execute(f'SELECT MAX({sf}) m FROM {src}')
        m = cur.fetchone()['m']
        conn.close()
        if not m: break
        if isinstance(m, datetime):
            last_time = (m + timedelta(seconds=1)).strftime('%Y-%m-%d %H:%M:%S')
        else:
            last_time = str(m)
    return total

print('=== 翻页同步 orders ===')
n = page_sync('orders', 'orders', 'updated_at', 200, 15)
print(f'\norders 同步累计: {n} 行')

conn = pymysql.connect(database='container_center', **CONN)
cur = conn.cursor()
cur.execute('SELECT COUNT(*) c FROM orders')
oc = cur.fetchone()['c']
cur.execute('SELECT COUNT(*) c FROM process_sub_steps')
sc = cur.fetchone()['c']
cur.execute('SELECT COUNT(*) c FROM process_records')
rc = cur.fetchone()['c']
conn.close()
print(f'\n当前 container_center: orders={oc}/364  sub_steps={sc}  records={rc}')
