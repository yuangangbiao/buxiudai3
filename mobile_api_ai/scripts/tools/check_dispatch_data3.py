import urllib.request, json

def fetch(url):
    try:
        r = urllib.request.urlopen(url, timeout=5)
        return json.loads(r.read().decode())
    except Exception as e:
        return {'error': str(e)}

BASE_5008 = 'http://127.0.0.1:5008'
BASE_5003 = 'http://127.0.0.1:5003'
order = 'ORD-202604290001'

# 1. 调度中心 processes API (app.py, 5008) - 通过 dispatch_center_bp
print('=' * 60)
print(f'调度中心 API 数据对比 (订单: {order})')
print('=' * 60)

print(f'\n--- [5008] /api/dispatch-center/processes ---')
d = fetch(f'{BASE_5008}/api/dispatch-center/processes')
if isinstance(d, list):
    for p in d:
        on = p.get('order_no', '')
        sn = p.get('step_name', '?')
        if order in on or '20260429' in on:
            print(f'  {sn:12s} | cq={p.get("completed_qty","?")} | rq={p.get("required_qty","?")}')
else:
    print(f'  {d}')

# 2. 调度中心 process (app.py, 5008)
print(f'\n--- [5008] /api/dispatch-center/processes (全部 ORDER-20260429) ---')
d = fetch(f'{BASE_5008}/api/dispatch-center/processes')
if isinstance(d, list):
    for p in d:
        on = p.get('order_no', '')
        if '20260429' in on:
            pid = p.get('id', '')[:8]
            sn = p.get('step_name', '?')
            print(f'  [{pid}] {on} | {sn:12s} | cq={p.get("completed_qty","?")} | rq={p.get("required_qty","?")} | status={p.get("status","?")}')

# 3. 子步骤 summary
print(f'\n--- [5008] /api/dispatch-center/process_sub_step_summary/ ---')
for p in d if isinstance(d, list) else []:
    pid = p.get('id', '')
    on = p.get('order_no', '')
    if order in on and pid:
        try:
            r = urllib.request.urlopen(f'{BASE_5008}/api/dispatch-center/process_sub_step_summary/{pid}', timeout=5)
            data = json.loads(r.read().decode())
            print(f'  Process: {p.get("step_name","?")} (id={pid[:8]})')
            if isinstance(data, list):
                for s in data:
                    print(f'    - {s.get("step_name","?"):12s} | total_qty={s.get("total_qty","?")}')
            else:
                print(f'    {data}')
        except Exception as e:
            print(f'    FAILED: {e}')

# 4. 报工系统 API (legacy_routes, 5008)
print(f'\n--- [5008] /process_sub_step_summary/ (legacy_routes) ---')
try:
    r = urllib.request.urlopen(f'{BASE_5008}/process_sub_step_summary/{order}', timeout=5)
    data = json.loads(r.read().decode())
    for s in data:
        print(f'  {s.get("step_name","?"):12s} | total_qty={s.get("total_qty","?")}')
except Exception as e:
    print(f'  {e}')

# 5. 报工系统 processes (legacy_routes, 5008)
print(f'\n--- [5008] /processes (legacy_routes) ---')
try:
    r = urllib.request.urlopen(f'{BASE_5008}/processes', timeout=5)
    data = json.loads(r.read().decode())
    for p in data:
        if order in p.get('order_no', ''):
            print(f'  {p.get("step_name","?"):12s} | cq={p.get("completed_qty","?")} | rq={p.get("required_qty","?")} | total={p.get("total_completed_qty","?")}')
except Exception as e:
    print(f'  {e}')

print('\n' + '=' * 60)
print('检查完成')
