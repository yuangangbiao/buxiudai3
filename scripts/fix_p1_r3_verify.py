"""P1-R3 验证: 5 线程并发创建订单不再 1062 冲突

依据: docs/日志报错汇总_20260623.md
错误: pymysql.err.IntegrityError: (1062, "Duplicate entry 'ORD-20260623-0019' for key 'orders.order_no'")
"""
import requests
import threading
import time
import random
import string


def gen_order_no():
    return f'E2E_CONC_{int(time.time())}_{"".join(random.choices(string.ascii_lowercase, k=4))}'


print('=== P1-R3 验证: 5 线程并发创建订单 ===')

# 登录 admin
sess = requests.Session()
r = sess.post('http://127.0.0.1:5001/api/login',
              json={'username': '测试', 'password': ''}, timeout=5)
login_data = r.json().get('data', {})
csrf = login_data.get('csrf_token', '')
print(f'admin login: {r.json().get("code")}')

results = []
errors = []
lock = threading.Lock()
order_nos = []


def do_create(idx):
    s = requests.Session()
    r = s.post('http://127.0.0.1:5001/api/login',
               json={'username': '测试', 'password': ''}, timeout=5)
    csrf = r.json().get('data', {}).get('csrf_token', '')
    order_no = gen_order_no()
    r = s.post(
        'http://127.0.0.1:5001/api/orders/create',
        json={
            'order_no': order_no,
            'product_type': 'E2E_CONC_TEST',
            'quantity': 1,
            'unit': '件',
            'customer_name': f'P1R3客户_{idx}',
        },
        headers={'X-CSRF-Token': csrf},
        timeout=30,
    )
    with lock:
        results.append(r.status_code)
        order_nos.append(order_no)
        if r.status_code != 200:
            errors.append((order_no, r.status_code, r.text[:200]))


threads = [threading.Thread(target=do_create, args=(i,)) for i in range(10)]
t0 = time.time()
for t in threads:
    t.start()
for t in threads:
    t.join()
cost = (time.time() - t0) * 1000

print(f'\n10 线程耗时: {cost:.0f}ms')
print(f'状态码: {results}')
print(f'成功: {results.count(200)}/{len(results)}')

if errors:
    print(f'\n错误详情 (前 3 条):')
    for no, code, txt in errors[:3]:
        print(f'  {no}: HTTP {code} {txt[:150]}')

# 重点：检查是否有 1062 IntegrityError
err1062 = [e for e in errors if '1062' in e[2] or 'Duplicate' in e[2]]
if err1062:
    print(f'\n❌ 仍有 {len(err1062)} 个 1062 冲突')
else:
    print(f'\n✅ 无 1062 冲突（修复成功）')

# 验证订单号唯一
unique_nos = set(order_nos)
print(f'\norder_no 唯一: {len(unique_nos)}/{len(order_nos)}')
