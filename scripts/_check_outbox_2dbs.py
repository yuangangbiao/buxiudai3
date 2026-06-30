"""查 2 个库是否有 outbox"""
import pymysql

for db in ['container_center', 'steel_belt']:
    conn = pymysql.connect(
        host='127.0.0.1', port=3306, user='root', password='88888888',
        database=db, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor,
    )
    with conn.cursor() as cur:
        cur.execute("SHOW TABLES LIKE 'outbox'")
        r = cur.fetchone()
        print(f'{db}.outbox: {bool(r)}')
        if r:
            cur.execute('SELECT COUNT(*) AS cnt FROM outbox')
            print(f'  count: {cur.fetchone()["cnt"]}')
    conn.close()
