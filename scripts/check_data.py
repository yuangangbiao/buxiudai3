import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.database import get_connection

conn = get_connection()
try:
    cursor = conn.cursor()

    cursor.execute("SHOW COLUMNS FROM orders LIKE 'product_type'")
    col = cursor.fetchone()
    print('[product_type列] 存在' if col else '[product_type列] 不存在')
    if col:
        print('  类型:', col['Type'])

    cursor.execute('SELECT COUNT(*) as cnt FROM orders')
    print('[orders表] 总记录数:', cursor.fetchone()['cnt'])

    cursor.execute('SELECT COUNT(*) as cnt FROM orders WHERE is_deleted = 0')
    print('[orders表] 未删除:', cursor.fetchone()['cnt'])

    cursor.execute("SELECT COUNT(*) as cnt FROM orders WHERE is_deleted = 0 AND status NOT IN ('已完成','已归档','已取消')")
    print('[orders表] 未删除+未完成:', cursor.fetchone()['cnt'])

    cursor.execute('SELECT id, order_no, status, created_at, is_deleted FROM orders ORDER BY id DESC LIMIT 5')
    print('[orders表] 最近5条:')
    for r in cursor.fetchall():
        print(f'  id={r["id"]}, order_no={r["order_no"]}, status={r["status"]}, created_at={r["created_at"]}, is_deleted={r["is_deleted"]}')

    cursor.execute('SELECT COUNT(*) as cnt FROM production_orders')
    print('[production_orders表] 总记录数:', cursor.fetchone()['cnt'])

    cursor.execute("SELECT COUNT(*) as cnt FROM production_orders WHERE status != '已取消'")
    print('[production_orders表] 未取消:', cursor.fetchone()['cnt'])

    cursor.execute('SELECT po.id, po.order_no, po.status, po.order_id FROM production_orders po ORDER BY po.id DESC LIMIT 5')
    print('[production_orders] 最近5条:')
    for r in cursor.fetchall():
        print(f'  id={r["id"]}, order_no={r["order_no"]}, status={r["status"]}, order_id={r["order_id"]}')

    cursor.execute('SELECT COUNT(*) as cnt FROM production_orders po JOIN orders o ON po.order_id = o.id')
    print('[JOIN匹配] production_orders+orders:', cursor.fetchone()['cnt'])

    cursor.execute("SELECT COUNT(*) as cnt FROM production_orders po JOIN orders o ON po.order_id = o.id WHERE o.created_at >= DATE_SUB(NOW(), INTERVAL 90 DAY)")
    print('[90天内] JOIN匹配:', cursor.fetchone()['cnt'])

    cursor.execute('SELECT COUNT(*) as cnt FROM quality_records')
    print('[quality_records表] 总记录数:', cursor.fetchone()['cnt'])

    cursor.close()
finally:
    conn.close()
