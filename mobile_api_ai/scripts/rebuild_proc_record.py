import sqlite3, json

db_path = 'd:/yuan/不锈钢网带跟单3.0/mobile_api_ai/wechat_container.db'
db = sqlite3.connect(db_path)
cur = db.cursor()

# 获取 process_records 表结构
cur.execute('PRAGMA table_info(process_records)')
print('=== process_records 表结构 ===')
for r in cur.fetchall():
    print(f'  {r}')

# 看 WO-202605006 的 steps
cur.execute('SELECT steps FROM process_records WHERE order_no=?', ('WO-202605006',))
steps_raw = cur.fetchone()[0]
print(f'\n=== WO-202605006 steps ===')
print(steps_raw[:500])

db.close()

# 查看 data_packages 的 content 中 WO-202605005 的 fields
with open('d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center_data.json', 'r', encoding='utf-8') as f:
    cache_data = json.load(f)

print(f'\n=== 缓存中 WO-202605005 / ORD-202604210003 的数据 ===')
for p in cache_data.get('processes', []):
    if p.get('order_no') in ('WO-202605005', 'ORD-202604210003') or p.get('order_no') in ('WO-202605005',):
        for k, v in p.items():
            if k == 'steps':
                if isinstance(v, list):
                    step_names = [s.get('name','?') if isinstance(s,dict) else s for s in v]
                    print(f'  {k}: {step_names}')
                else:
                    print(f'  {k}: {v}')
            else:
                print(f'  {k}: {v}')
        print()
