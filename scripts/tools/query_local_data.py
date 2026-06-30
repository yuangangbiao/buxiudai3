"""
查询本地 SQLite + JSON 存储的实际内容
"""
import sqlite3, os, json

DB = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'
JS = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\dispatch_center_data.json'

print('=' * 60)
print('一、SQLite 数据库')
print('=' * 60)
conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = c.fetchall()
for t in tables:
    tn = t[0]
    c.execute(f'SELECT COUNT(*) FROM [{tn}]')
    cnt = c.fetchone()[0]
    print(f'  [{tn}] {cnt} 条')

    if tn in ('data_packages', 'process_records', 'dispatch_commands', 'data_flow_logs', 'material_requirements'):
        c.execute(f'SELECT * FROM [{tn}] LIMIT 3')
        rows = c.fetchall()
        if rows:
            col_names = [d[0] for d in c.description]
            for r in rows:
                d = dict(zip(col_names, r))
                display = {}
                for k, v in d.items():
                    if k in ('id', 'data_type', 'title', 'content', 'status', 'target_operator',
                             'operator_id', 'related_order', 'related_process', 'order_no',
                             'product_name', 'process_name', 'current_step', 'steps',
                             'command_type', 'command_status', 'event_type', 'event_data',
                             'material_id', 'material_name', 'spec', 'required_qty', 'prepared_qty', 'unit',
                             'created_at', 'updated_at'):
                        display[k] = str(v)[:80]
                print(f'    -> {json.dumps(display, ensure_ascii=False)}')
            if cnt > 3:
                print(f'    ... 还有 {cnt-3} 条')
        else:
            print('    (空)')
    print()
conn.close()

print()
print('=' * 60)
print('二、JSON 缓存文件')
print('=' * 60)
if os.path.exists(JS):
    size = os.path.getsize(JS)
    print(f'  文件大小: {size/1024:.1f} KB')
    with open(JS, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, list):
                print(f'  [{k}] {len(v)} 项')
                for item in v[:2]:
                    if isinstance(item, dict):
                        keys = ('id','order_no','process_name','status','task_name','content','operator')
                        s = json.dumps({kk: str(vv)[:80] for kk, vv in item.items() if kk in keys}, ensure_ascii=False)
                        print(f'    -> {s}')
                if len(v) > 2:
                    print(f'    ... 还有 {len(v)-2} 项')
            elif isinstance(v, dict):
                s = json.dumps({kk: str(vv)[:80] for kk, vv in list(v.items())[:5]}, ensure_ascii=False)
                print(f'  [{k}] {s}')
            else:
                print(f'  [{k}] {str(v)[:120]}')
    elif isinstance(data, list):
        print(f'  数组 {len(data)} 项')
else:
    print('  (文件不存在)')
