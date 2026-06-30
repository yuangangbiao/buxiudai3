"""翻页同步 - 用 datetime 修复参数类型"""
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

def page_sync(src, tgt, sf, page_size=200, max_iter=20):
    last_time = datetime(1000, 1, 1, 0, 0, 0)
    total = 0
    for i in range(max_iter):
        n = _sync_table(src, tgt, sf, page_size, last_time)
        if n == 0:
            print(f'  iter {i+1}: 0 行 累计 {total}')
            break
        total += n
        print(f'  iter {i+1}: 同步 {n} 行 累计 {total}')
        conn = pymysql.connect(database='steel_belt', **CONN)
        cur = conn.cursor()
        cur.execute(f'SELECT MAX({sf}) m FROM {src}')
        m = cur.fetchone()['m']
        conn.close()
        if not m: break
        if isinstance(m, datetime):
            last_time = m + timedelta(seconds=1)
        else:
            last_time = datetime.now()
    return total

print('=== 翻页同步 orders (datetime 参数) ===')
n = page_sync('orders', 'orders', 'updated_at', 200, 20)
print(f'\norders 同步累计: {n} 行')

# 检查
conn = pymysql.connect(database='container_center', **CONN)
cur = conn.cursor()
cur.execute('SELECT COUNT(*) c FROM orders')
oc = cur.fetchone()['c']
cur.execute('SELECT COUNT(*) c FROM process_sub_steps')
sc = cur.fetchone()['c']
cur.execute('SELECT COUNT(*) c FROM process_records')
rc = cur.fetchone()['c']
conn.close()
print(f'\ncontainer_center: orders={oc}/364  sub_steps={sc}  records={rc}')
