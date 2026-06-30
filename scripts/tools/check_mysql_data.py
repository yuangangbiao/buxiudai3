import pymysql, os
from pymysql.cursors import DictCursor

MYSQL_HOST = os.environ.get('MYSQL_HOST', '127.0.0.1')
MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE', 'steel_belt')

conn = pymysql.connect(
    host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER,
    password=MYSQL_PASSWORD, database=MYSQL_DATABASE,
    charset='utf8mb4', cursorclass=DictCursor
)
c = conn.cursor()

c.execute('SELECT COUNT(*) as cnt FROM production_orders')
print('production_orders total:', c.fetchone()['cnt'])

c.execute("""SELECT work_order_no, order_no, status FROM production_orders 
WHERE status NOT IN ("已完成","已发货","订单完成") 
AND (is_deleted=0 OR is_deleted IS NULL) 
ORDER BY updated_at DESC LIMIT 20""")
rows = c.fetchall()
print('production_orders 非终态:', len(rows), '条')
for r in rows:
    print(' ', r['work_order_no'], '|', r.get('order_no',''), '|', r['status'])

c.execute('SELECT COUNT(*) as cnt FROM process_records')
print('process_records total:', c.fetchone()['cnt'])

c.execute("""SELECT DISTINCT work_order_no FROM process_records 
WHERE work_order_no IS NOT NULL AND work_order_no!="" LIMIT 30""")
wos = c.fetchall()
print('process_records 不同订单:', len(wos), '个')
for r in wos:
    print(' ', r['work_order_no'])

conn.close()
