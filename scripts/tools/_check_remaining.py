"""查剩余扫码失败订单"""
import pymysql
CONN = dict(host='127.0.0.1', port=3306, user='root', password='88888888', connect_timeout=5, cursorclass=pymysql.cursors.DictCursor)
conn = pymysql.connect(database='container_center', **CONN)
cur = conn.cursor()
for code in ['ORD-202604200001', 'GO-AUTO-001']:
    print(f'\n=== {code} ===')
    for tbl in ['orders','process_records','process_sub_steps','production_orders','data_packages']:
        try:
            cur.execute(f'SELECT COUNT(*) c FROM {tbl} WHERE order_no=%s', (code,))
            c = cur.fetchone()['c']
            print(f'  {tbl:25s} {c}')
        except Exception as e:
            print(f'  {tbl}: ERR {e}')
conn.close()
