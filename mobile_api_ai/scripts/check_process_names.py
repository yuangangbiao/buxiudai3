import sqlite3, json
db = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'
conn = sqlite3.connect(db)
cur = conn.cursor()
print('=== dispatch_commands process_name ===')
cur.execute('SELECT DISTINCT process_name FROM dispatch_commands WHERE process_name IS NOT NULL AND process_name != ""')
for r in cur.fetchall(): print(' |', r[0])
print('=== data_packages related_process ===')
cur.execute('SELECT DISTINCT related_process FROM data_packages WHERE related_process IS NOT NULL AND related_process != ""')
for r in cur.fetchall(): print(' |', r[0])
print('=== process_records steps ===')
cur.execute('SELECT steps FROM process_records WHERE steps IS NOT NULL AND steps != ""')
for r in cur.fetchall():
    try:
        steps = json.loads(r[0])
        for s in steps:
            name = s.get('name', '') if isinstance(s, dict) else s
            print(' |', name)
    except Exception as e:
        print(f' | (解析失败: {e})')
conn.close()