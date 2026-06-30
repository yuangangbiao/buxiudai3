"""测 ETL 物料同步"""
import sys, os
sys.path.insert(0, r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai')
os.chdir(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai')
from dotenv import load_dotenv
load_dotenv(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\.env')
import logging
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
from etl_local_mirror import _run_etl_cycle
import pymysql
CONN = dict(host='127.0.0.1', port=3306, user='root', password='88888888', connect_timeout=5, cursorclass=pymysql.cursors.DictCursor)
print('=== ETL 一轮同步 (含 order_materials) ===')
n = _run_etl_cycle()
print(f'ETL 同步: {n} 行')
conn = pymysql.connect(database='container_center', **CONN)
cur = conn.cursor()
cur.execute('SELECT COUNT(*) c FROM material_records')
print(f'container_center.material_records: {cur.fetchone()["c"]}')
cur.execute('SELECT COUNT(*) c FROM outsource_records')
print(f'container_center.outsource_records: {cur.fetchone()["c"]}')
conn.close()
