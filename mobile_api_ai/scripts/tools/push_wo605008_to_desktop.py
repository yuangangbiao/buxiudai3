import sqlite3, json, requests, os

cc_db = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'
desktop_url = 'http://localhost:8008/api/container/webhook'

print('=== 1. Get WO-202605008 Data ===')
conn = sqlite3.connect(cc_db)
cur = conn.cursor()

rows = cur.execute("SELECT * FROM process_records WHERE order_no LIKE '%202605008%'").fetchall()
cols = [description[0] for description in cur.description]
print(f'Found {len(rows)} process_records')

if rows:
    record = dict(zip(cols, rows[0]))
    print(f'OrderNo: {record.get("order_no")}')
    print(f'Status: {record.get("status")}')
    print(f'CurrentStep: {record.get("current_step")}')

    print('\n=== 2. Push To Desktop ===')

    payload = {
        'event_type': 'process_updated',
        'data': record
    }

    try:
        resp = requests.post(desktop_url, json=payload, timeout=10)
        print(f'Response: {resp.status_code}')
        print(f'Body: {resp.text[:500]}')

        if resp.status_code == 200:
            result = resp.json()
            if result.get('code') == 0:
                print('\n[PASS] Push Success!')
            else:
                print(f'\n[FAIL] Push Failed: {result.get("message")}')
        else:
            print(f'\n[FAIL] HTTP Error: {resp.status_code}')
    except Exception as e:
        print(f'\n[FAIL] Push Exception: {e}')

conn.close()

print('\n=== 3. Verify Desktop Data ===')
backend_db = r'd:\yuan\backend\data\chengsheng.db'
if os.path.exists(backend_db):
    conn2 = sqlite3.connect(backend_db)
    cur2 = conn2.cursor()
    rows2 = cur2.execute("SELECT * FROM container_sync_records WHERE order_no LIKE '%202605008%'").fetchall()
    if rows2:
        cols2 = [description[0] for description in cur2.description]
        for r in rows2:
            rec = dict(zip(cols2, r))
            print(f'order_no: {rec.get("order_no")}')
            print(f'order_no: {rec.get("order_no")}')
            print(f'status: {rec.get("status")}')
            print(f'sync_status: {rec.get("sync_status")}')
    else:
        print('Desktop Still Has No WO-202605008 Record')
    conn2.close()
else:
    print(f'Database Not Found: {backend_db}')
