import requests, json

r1 = requests.get('http://localhost:5008/api/dashboard', timeout=10)
print('=== /api/dashboard ===')
d = r1.json()
print(json.dumps(d, ensure_ascii=False, indent=2))

r2 = requests.get('http://localhost:5008/api/sub_step_records?order_no=ORD-202605008', timeout=10)
print('\n=== /api/sub_step_records?order_no=ORD-202605008 ===')
records = r2.json()
print(f'共 {len(records)} 条记录')
for r in records[:5]:
    print(json.dumps(r, ensure_ascii=False))

r3 = requests.get('http://localhost:5008/api/scan-info?code=WO-202605008', timeout=10)
print('\n=== /api/scan-info?code=WO-202605008 ===')
scan = r3.json()
data = scan.get('data', {})
print(f'processes: {len(data.get("processes", []))} 个')
print(f'tasks: {len(data.get("tasks", []))} 个')
for t in data.get('tasks', [])[:3]:
    print(f'  {t.get("process_name")}: completed_qty={t.get("completed_qty")}')
