"""Check process steps for ORD-202604210003"""
import sqlite3, json

db = 'D:\\yuan\\不锈钢网带跟单3.0\\mobile_api_ai\\chengsheng.db'
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

order_id = 'ORD-202604210003'

# 1. order_processes
print('=== order_processes ===')
cur.execute('SELECT * FROM order_processes WHERE order_id=? ORDER BY sequence', (order_id,))
rows = cur.fetchall()
print('共 %d 条' % len(rows))
for r in rows:
    print('  [%d] %s' % (r['sequence'], r['process_key']))

# 2. container_sync_records.steps JSON
print()
print('=== container_sync_records.steps ===')
cur.execute('SELECT steps, task_count, completed_task_count FROM container_sync_records WHERE order_no=?', (order_id,))
r = cur.fetchone()
if r:
    print('task_count: %s' % r['task_count'])
    print('completed_task_count: %s' % r['completed_task_count'])
    steps_str = r['steps']
    print('steps原始长度: %d chars' % len(steps_str))
    try:
        steps = json.loads(steps_str)
        print('解析后共 %d 道工序:' % len(steps))
        for i, s in enumerate(steps):
            if isinstance(s, dict):
                name = s.get('name', '') or s.get('step_name', '') or '?'
                pk = s.get('process_key', '') or ''
                print('  [%d] %s (key=%s)' % (i, name, pk))
            else:
                print('  [%d] %s' % (i, str(s)))
    except Exception as e:
        print('JSON解析失败: %s' % e)
        print('steps前500字符: %s' % steps_str[:500])
else:
    print('无数据')

# 3. 检查同步脚本是否跳过了某些步骤
print()
print('=== 对比: 容器中心原始 steps ===')
cc_db = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'
conn2 = sqlite3.connect(cc_db)
conn2.row_factory = sqlite3.Row
cur2 = conn2.cursor()
cur2.execute('SELECT steps, order_no FROM process_records WHERE order_no=?', (order_id,))
r2 = cur2.fetchone()
if r2:
    print('order_no: %s' % r2['order_no'])
    steps_str2 = r2['steps']
    print('steps原始长度: %d chars' % len(steps_str2))
    try:
        steps2 = json.loads(steps_str2)
        print('容器中心共 %d 道工序:' % len(steps2))
        for i, s in enumerate(steps2):
            if isinstance(s, dict):
                name = s.get('name', '') or s.get('step_name', '') or '?'
                print('  [%d] %s' % (i, name))
            else:
                print('  [%d] %s' % (i, str(s)))
    except Exception as e:
        print('JSON解析失败: %s' % e)
        print('steps前500字符: %s' % steps_str2[:500])
else:
    print('process_records中未找到 order_no=%s' % order_id)
conn2.close()

conn.close()
