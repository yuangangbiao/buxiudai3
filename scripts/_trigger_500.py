"""触发 500 路径 + 验证 record_error"""
import os, time, urllib.request, urllib.error, json

# 1. 创建标记文件
open(r'd:\yuan\不锈钢网带跟单3.0\.tmp_simulate_500', 'w').close()
print('[1] 创建 .tmp_simulate_500 标记')

# 2. 调一次 my-tasks,应该走 500 路径
print('[2] 调 my-tasks (期望 500)...')
try:
    r = urllib.request.urlopen('http://127.0.0.1:5008/api/process/my-tasks?worker_id=test_500', timeout=8)
    print('  status=%d body=%s' % (r.status, r.read().decode('utf-8', errors='replace')[:300]))
except urllib.error.HTTPError as e:
    body = e.read().decode('utf-8', errors='replace')[:300] if e.fp else ''
    print('  status=%d body=%s' % (e.code, body))

# 3. 验证 metrics
print('[3] 检查 /api/metrics/stats ...')
time.sleep(1)
r = urllib.request.urlopen('http://127.0.0.1:5008/api/metrics/stats?minutes=5', timeout=5)
data = json.loads(r.read().decode('utf-8', errors='replace'))['data']
print('  api.total_requests =', data['api']['total_requests'])
print('  api.status_codes   =', data['api']['status_codes'])
print('  errors.total       =', data['errors']['total'])
print('  errors.by_type     =', data['errors']['by_type'])
print('  recent errors:')
for e in data['errors'].get('recent', []):
    print('    -', e.get('error_type'), '|', e.get('message')[:80], '| endpoint=', e.get('endpoint'))

# 4. 删标记文件
os.remove(r'd:\yuan\不锈钢网带跟单3.0\.tmp_simulate_500')
print('[4] 删除 .tmp_simulate_500 标记')
