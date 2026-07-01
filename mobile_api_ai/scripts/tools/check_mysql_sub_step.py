import os, pymysql
from pymysql.cursors import DictCursor

cfg = {
    'host': os.environ.get('MYSQL_HOST', 'localhost'),
    'port': int(os.environ.get('MYSQL_PORT', 3306)),
    'user': os.environ.get('MYSQL_USER', 'root'),
    'password': os.environ.get('MYSQL_PASSWORD', ''),
    'database': os.environ.get('MYSQL_DATABASE', 'steel_belt'),
    'charset': 'utf8mb4',
}
info = '{}@{}:{}/{}'.format(cfg['user'], cfg['host'], cfg['port'], cfg['database'])
print('MySQL: ' + info)

try:
    conn = pymysql.connect(**cfg, cursorclass=DictCursor, connect_timeout=3)
    c = conn.cursor()

    print('\n=== 1. 工单状态 ===')
    c.execute('SELECT id, order_no, status FROM production_orders WHERE order_no=%s', ('WO202605009',))
    po = c.fetchone()
    if po:
        print('production_orders: id={}, status={}'.format(po['id'], po['status']))
        po_id = po['id']
    else:
        print('production_orders 中未找到')
        po_id = None

    if po_id:
        c.execute('SELECT id, process_name, completed_qty, worker, updated_at FROM process_records WHERE production_id=%s ORDER BY process_name', (po_id,))
        rows = c.fetchall()
        if rows:
            print('\n=== 2. process_records 报工记录 ({} 条) ==='.format(len(rows)))
            for r in rows:
                qty = r['completed_qty'] or 0
                w = r['worker'] or '-'
                print('  id={}  工序={}  completed_qty={}  worker={}  updated_at={}'.format(
                    r['id'], r['process_name'], qty, w, r['updated_at']))
        else:
            print('\n=== 2. process_records 中无报工记录 ===')

    c.execute('SELECT id, order_no, status FROM orders WHERE order_no=%s', ('WO202605009',))
    o = c.fetchone()
    if o:
        print('\norders: id={}, status={}'.format(o['id'], o['status']))

    conn.close()

    print('\n=== 结论 ===')
    print('报工数据存到 MySQL 的 process_records 表的 completed_qty（完成量）和 worker（操作人）字段')
    if po_id:
        print('工单 WO202605009 在 MySQL 中存在')
    else:
        print('工单 WO202605009 在 MySQL 中不存在')

except pymysql.err.OperationalError as e:
    print('\nMySQL 连接失败: ' + str(e))
except Exception as e:
    print('\n查询异常: ' + str(e))
