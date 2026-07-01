import sqlite3, os

cc_db = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'
backend_db = r'd:\yuan\backend\data\chengsheng.db'

print('=== 容器中心 WO-202605008 状态 ===')
if os.path.exists(cc_db):
    conn = sqlite3.connect(cc_db)
    cur = conn.cursor()
    rows = cur.execute("SELECT id, order_no, status, current_step, updated_at FROM process_records WHERE order_no LIKE '%202605008%'").fetchall()
    for r in rows:
        print(f'OrderNo: {r[1]}, Status: {r[2]}, CurrentStep: {r[3]}, UpdatedAt: {r[4]}')
    conn.close()

print('\n=== 自动跟单系统 WO-202605008 状态 ===')
if os.path.exists(backend_db):
    conn2 = sqlite3.connect(backend_db)
    cur2 = conn2.cursor()
    
    print('\n--- production_orders ---')
    rows = cur2.execute("SELECT * FROM production_orders WHERE order_no LIKE '%202605008%'").fetchall()
    if rows:
        for r in rows:
            print(f'order_no: {r[1]}, status: {r[9]}, assigned_to: {r[7]}')
    else:
        print('没有找到记录')
    
    print('\n--- container_sync_records ---')
    rows = cur2.execute("SELECT id, order_no, order_no, status, sync_status, updated_at FROM container_sync_records WHERE order_no LIKE '%202605008%'").fetchall()
    if rows:
        for r in rows:
            print(f'ID: {r[0]}, order_no: {r[1]}, order_no: {r[2]}, status: {r[3]}, sync_status: {r[4]}, updated_at: {r[5]}')
    else:
        print('没有找到记录')
    
    conn2.close()
else:
    print(f'数据库不存在: {backend_db}')
