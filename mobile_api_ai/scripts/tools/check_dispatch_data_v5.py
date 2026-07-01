"""
深入排查调度中心数据问题
"""
import urllib.request, json

def fetch_json(url):
    try:
        r = urllib.request.urlopen(url, timeout=5)
        return json.loads(r.read().decode())
    except Exception as e:
        return {'_error': str(e)}

BASE = 'http://127.0.0.1:5008'
order = 'ORD-202604290001'

# 1. 获取 dispatch-center 的所有 processes，拿到 ORD-202604290001 的 process_id
d = fetch_json(f'{BASE}/api/dispatch-center/processes')
processes = (d.get('data') or []) if isinstance(d, dict) and d.get('code') == 0 else (d if isinstance(d, list) else [])
target = next((p for p in processes if order in p.get('order_no','')), None)
if not target:
    print('❌ 未找到 ORD-202604290001 的 dispatch-center process')
    exit()
pid = target.get('id', '')
print(f'进程ID: {pid}')
print(f'step_name: {target.get("step_name","?")}')

# 2. 查这个 process_id 在容器中心中的 sub_steps
print(f'\n--- 容器中心 /api/container-center/sub_steps/{pid} ---')
cc_steps = fetch_json(f'{BASE}/api/container-center/sub_steps/{pid}')
# 也尝试带/不带前缀
cc_steps2 = fetch_json(f'http://127.0.0.1:5002/api/sub_steps/{pid}')
print(f'  5008: {json.dumps(cc_steps, ensure_ascii=False, default=str)[:300]}')
print(f'  5002: {json.dumps(cc_steps2, ensure_ascii=False, default=str)[:300]}')

# 3. 查这个 process_id 在容器中心中的 sub_step_summary
print(f'\n--- 容器中心 /api/container-center/sub_step_summary/{pid} ---')
cc_summary = fetch_json(f'{BASE}/api/container-center/sub_step_summary/{pid}')
print(f'  {json.dumps(cc_summary, ensure_ascii=False, default=str)[:300]}')

# 4. 查容器中心中 ORD-202604290001 的所有 sub_steps（按订单号查）
print(f'\n--- 容器中心中 ORD-202604290001 的所有 sub_steps ---')
# 先看看容器中心有哪些API
cc_all = fetch_json(f'http://127.0.0.1:5002/api/sub_steps')
if isinstance(cc_all, list):
    for s in cc_all:
        if order in s.get('order_no',''):
            print(f'  step={s.get("step_name","?")} qty={s.get("quantity","?")} pid={s.get("process_id","?")[:12]} batch={s.get("batch_no","?")}')
elif isinstance(cc_all, dict):
    items = cc_all.get('data', []) if cc_all.get('code') == 0 else []
    for s in items:
        if order in s.get('order_no',''):
            print(f'  step={s.get("step_name","?")} qty={s.get("quantity","?")} pid={s.get("process_id","?")[:12]} batch={s.get("batch_no","?")}')

# 5. legacy_routes processes
print(f'\n--- 报工系统 /process_sub_step_summary/{order} ---')
try:
    r = urllib.request.urlopen(f'{BASE}/process_sub_step_summary/{order}', timeout=5)
    print(f'  {json.dumps(json.loads(r.read().decode()), ensure_ascii=False, default=str)[:500]}')
except Exception as e:
    print(f'  ❌ {e}')

# 6. 检查 dispatch center process detail 为什么 500
print(f'\n--- 调度中心 process detail ({pid}) ---')
detail = fetch_json(f'{BASE}/api/dispatch-center/processes/{pid}')
print(f'  结果: {json.dumps(detail, ensure_ascii=False, default=str)[:500]}')
