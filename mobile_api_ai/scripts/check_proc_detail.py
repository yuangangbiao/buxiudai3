import sqlite3, json

db_path = 'd:/yuan/不锈钢网带跟单3.0/mobile_api_ai/wechat_container.db'
db = sqlite3.connect(db_path)
cur = db.cursor()

# 查看 WO-202605006 的完整 process_record
cur.execute('SELECT * FROM process_records WHERE order_no=?', ('WO-202605006',))
cols = [d[0] for d in cur.description]
row = dict(zip(cols, cur.fetchone()))
print('=== WO-202605006 process_record 完整字段 ===')
for k, v in row.items():
    if k == 'steps':
        if isinstance(v, str):
            try:
                s = json.loads(v)
                print(f'  {k}: {json.dumps(s, ensure_ascii=False)[:200]}')
            except Exception as e:
                print(f'  {k}: {v} (JSON解析失败: {e})')
        else:
            print(f'  {k}: {v}')
    else:
        print(f'  {k}: {v}')

# 查看 data_packages 中 WO-202605005 的所有数据包  
print('\n=== WO-202605005 所有 data_packages ===')
cur.execute('SELECT id, related_order, related_process, data, content FROM data_packages WHERE related_order=?', ('WO-202605005',))
for r in cur.fetchall():
    pkg_id, related_order, related_process, data_str, content_str = r
    print(f'  pkg_id={pkg_id}, process={related_process}')
    if content_str:
        try:
            c = json.loads(content_str)
            print(f'    content: {json.dumps(c, ensure_ascii=False)[:300]}')
        except Exception as e:
            print(f'    content: {content_str[:200]} (JSON解析失败: {e})')

db.close()
