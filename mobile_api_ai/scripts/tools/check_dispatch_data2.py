import urllib.request, json

def fetch(url):
    try:
        r = urllib.request.urlopen(url, timeout=5)
        return json.loads(r.read().decode())
    except Exception as e:
        return {'error': str(e)}

order = 'ORD-202604290001'

print('=' * 60)
print(f'订单: {order}')
print('=' * 60)

# 1. 调度中心 processes API (5003)
print('\n--- 调度中心 (5003) /processes ---')
d = fetch('http://127.0.0.1:5003/processes')
if isinstance(d, list):
    for p in d:
        if p.get('order_no', '').startswith('ORD-20260429'):
            print(f"  {p.get('step_name','?'):12s} | completed_qty={p.get('completed_qty','?')} | required_qty={p.get('required_qty','?')}")
else:
    print(f'  {d}')

# 2. 调度中心 process_sub_step_summary (5003)
print('\n--- 调度中心 (5003) /process_sub_step_summary/ ---')
try:
    r = urllib.request.urlopen(f'http://127.0.0.1:5003/process_sub_step_summary/{order}', timeout=5)
    data = json.loads(r.read().decode())
    for s in data:
        print(f"  {s.get('step_name','?'):12s} | total_qty={s.get('total_qty','?')}")
except Exception as e:
    print(f'  {e}')

# 3. 报工系统 API (5008)
print('\n--- 报工系统 (5008) /process_sub_step_summary/ ---')
try:
    r = urllib.request.urlopen(f'http://127.0.0.1:5008/process_sub_step_summary/{order}', timeout=5)
    data = json.loads(r.read().decode())
    for s in data:
        print(f"  {s.get('step_name','?'):12s} | total_qty={s.get('total_qty','?')} | sub_steps={len(s.get('sub_steps',[]))}")
except Exception as e:
    print(f'  {e}')

# 4. 报工系统 processes (5008)
print('\n--- 报工系统 (5008) /processes ---')
try:
    r = urllib.request.urlopen('http://127.0.0.1:5008/processes', timeout=5)
    data = json.loads(r.read().decode())
    for p in data:
        if p.get('order_no', '').startswith('ORD-20260429'):
            print(f"  {p.get('step_name','?'):12s} | completed_qty={p.get('completed_qty','?')} | required_qty={p.get('required_qty','?')}")
except Exception as e:
    print(f'  {e}')

print('\n' + '=' * 60)
print('检查完成')
