"""测试提交报工并验证数据更新"""
import requests, json, sys

API = 'http://192.168.0.103:5008'

# Step 1: Get dashboard
r = requests.get(f'{API}/api/dashboard', timeout=5)
print(f'Dashboard: {r.status_code}')
d = r.json()
print(f'totalOrders={d.get("totalOrders")} todayReports={d.get("todayReports")}')
recent = d.get('recentRecords', [])
if not recent:
    print('No recent records found')
    sys.exit(1)

sample = recent[0]
order_id = sample.get('orderId', '')
print(f'Sample order: {order_id}')

# Step 2: Get scan-info
r2 = requests.get(f'{API}/api/scan-info?code={order_id}', timeout=5)
print(f'Scan-info: {r2.status_code}')
if r2.status_code != 200:
    print(f'Failed: {r2.text}')
    sys.exit(1)
data = r2.json().get('data', {})
processes = data.get('processes', [])
if not processes:
    print('No processes found')
    sys.exit(1)

# Step 3: Count sub_steps BEFORE submission
r_before = requests.get(f'{API}/api/sub_step_records', timeout=5)
records_before = r_before.json()
print(f'Records BEFORE submission: {len(records_before)}')

# Step 4: Submit a test report
proc = processes[0]
payload = {
    'process_id': proc['process_id'],
    'order_no': data['order_no'],
    'step_name': proc['process_name'],
    'quantity': 1,
    'operator': 'test_user',
    'remark': 'API test ' + str(hash(order_id))[:6]
}
print(f'Submitting: process_id={payload["process_id"]} step={payload["step_name"]} qty=1')
r3 = requests.post(f'{API}/api/process_sub_step', json=payload, timeout=5)
print(f'Submit result: {r3.status_code} {r3.text[:200]}')

# Step 5: Check scan-info again
r4 = requests.get(f'{API}/api/scan-info?code={order_id}', timeout=5)
if r4.status_code == 200:
    data2 = r4.json().get('data', {})
    for p in data2.get('processes', []):
        if p['process_name'] == payload['step_name']:
            print(f'After submit: completed_qty={p["completed_qty"]}')

# Step 6: Check sub_step_records AFTER submission
r_after = requests.get(f'{API}/api/sub_step_records', timeout=5)
records_after = r_after.json()
print(f'Records AFTER submission: {len(records_after)}')
print(f'New records: {len(records_after) - len(records_before)}')
if len(records_after) > len(records_before):
    new_record = records_after[0]
    print(f'Latest record: {json.dumps(new_record, ensure_ascii=False)}')
