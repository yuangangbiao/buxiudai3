import urllib.request
import json

BASE_URL = 'http://127.0.0.1:5002'
headers = {'Content-Type': 'application/json'}

def api_post(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(BASE_URL + path, data=body, headers=headers, method='POST')
    return json.loads(urllib.request.urlopen(req).read())

def api_get(path):
    req = urllib.request.Request(BASE_URL + path, method='GET')
    return json.loads(urllib.request.urlopen(req).read())

# 清理之前的记录
print('=== 1. 清理重复数据 ===')
r = api_post('/api/dispatch_commands/dedup', {})
print(f'清理结果: {r["data"]["deleted_count"]} 条')

# 发布新任务
print('\n=== 2. 发布工序任务 ===')
r1 = api_post('/api/internal/publish', {
    'task_type': 'report',
    'title': '编织工序测试',
    'content': {'quantity': 100},
    'operator_id': 'OP001',
    'related_order': '202605006',
    'related_process': '编织',
    'priority': 'normal'
})
print(f'code={r1.get("code")}, message={r1.get("message")}')

# 查询 dispatch_commands
print('\n=== 3. 直接查询数据库 ===')
import sqlite3
conn = sqlite3.connect(r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db')
conn.row_factory = sqlite3.Row
cur = conn.execute('SELECT command_id, order_no, process_name, created_at FROM dispatch_commands WHERE order_no=? ORDER BY created_at DESC', ('202605006',))
for r in cur:
    print(f'  cmd_id={r["command_id"]}, order={r["order_no"]!r}, process={r["process_name"]!r}, time={r["created_at"]}')
conn.close()
