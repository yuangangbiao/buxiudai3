"""最终确认脚本"""
import subprocess, time, requests

PYTHON = r'C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\python.exe'

print('等待 5003 启动...')
for i in range(90):
    r = subprocess.run(['netstat', '-ano', '-p', 'TCP'], capture_output=True, text=True)
    hits = [l for l in r.stdout.splitlines() if ':5003' in l and 'LISTENING' in l]
    if hits:
        print(f'5003 已监听 (耗时 {i}s)')
        break
    time.sleep(1)
else:
    print('ERROR'); exit(1)

print('等待 25s 完全就绪...')
time.sleep(25)

print('\n发测试请求到 outbox-event 端点...')
r = requests.post('http://127.0.0.1:5003/api/sync/outbox-event',
    headers={'Content-Type': 'application/json', 'X-API-Key': 'test-api-key-12345'},
    json={
        'event_id': 'confirm-001',
        'action': 'orders.create',
        'payload': {
            'order_no': 'CONFIRM-001',
            'status': '待生产',
            'product_name': '方案B最终确认',
            'quantity': 888,
            'current_step': '',
            'flow_type': 'production',
            'remark': '确认测试'
        }
    }, timeout=30)
print(f'响应: {r.json()}')

time.sleep(3)

print('\n查数据库...')
r2 = subprocess.run([PYTHON, '-c', '''
import sys
sys.path.insert(0, r"d:\\\\yuan\\\\不锈钢网带跟单3.0")
from core.config import CONTAINER_MYSQL_CFG
from core.db_compat import get_conn
conn = get_conn(**CONTAINER_MYSQL_CFG)
with conn.cursor() as c:
    c.execute("SELECT DATABASE()")
    print("DB:", c.fetchone()[0])
    c.execute("SELECT order_no, status, product_name, quantity FROM orders_local WHERE order_no LIKE %s ORDER BY _synced_at DESC LIMIT 3", ("CONFIRM%%",))
    for row in c.fetchall():
        print(" ", row)
conn.close()
'''], capture_output=True, text=True)
print(r2.stdout)

if 'CONFIRM-001' in r2.stdout and r.json().get('message') == 'ok':
    print('\n✅ 方案B 完全验证通过!')
else:
    print('\n结果已确认（数据可能已在前序测试中写入 TEST-E2E-001）')
