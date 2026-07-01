"""
对比调度中心与报工系统对 ORD-202604290001 的数据差异
"""
import urllib.request, json, sys

def fetch(url, label=''):
    try:
        r = urllib.request.urlopen(url, timeout=5)
        data = json.loads(r.read().decode())
        return data
    except Exception as e:
        return {'_error': str(e)}

order = 'ORD-202604290001'
BASE = 'http://127.0.0.1:5008'

print('=' * 65)
print(f'调度中心 vs 报工系统 数据对比 — {order}')
print(f'调度中心 → 端口 5008（app.py 注册 dispatch_center_bp）')
print(f'报工系统 → 端口 5008（app.py 注册 legacy_bp）')
print('=' * 65)

# ─── 1. 调度中心 processes ─────────────────────────────────
print('\n【1】调度中心 /api/dispatch-center/processes')
d = fetch(f'{BASE}/api/dispatch-center/processes')
if isinstance(d, list):
    print(f'  返回格式异常：是列表而不是 {{code, data}}')
    items = [p for p in d if order in p.get('order_no','')]
elif isinstance(d, dict):
    items = (d.get('data') or []) if d.get('code') == 0 else []
    items = [p for p in items if order in p.get('order_no','')]
else:
    items = []
print(f'  匹配条目: {len(items)}')
for p in items:
    print(f'  ├─ {p.get("step_name","?"):12s}')
    print(f'  ├─ completed_qty = {p.get("completed_qty","(不存在)")}')
    print(f'  ├─ required_qty = {p.get("required_qty","(不存在)")}')
    print(f'  ├─ quantity = {p.get("quantity","?")}')
    print(f'  ├─ status = {p.get("status","?")}')
    print(f'  ├─ current_step = {p.get("current_step","?")}')
    print(f'  ├─ task_count = {p.get("task_count","?")}')
    print(f'  ├─ completed_task_count = {p.get("completed_task_count","?")}')
    print(f'  └─ created_at = {p.get("created_at","?")}')

# ─── 2. 调度中心 process detail ───────────────────────────
print(f'\n【2】调度中心 /api/dispatch-center/processes/<id>（遍历详情）')
for p in items:
    pid = p.get('id','')
    if not pid:
        continue
    d2 = fetch(f'{BASE}/api/dispatch-center/processes/{pid}')
    print(f'  ├─ id={pid[:12]} step={p.get("step_name","?")}')
    if isinstance(d2, dict):
        print(f'  ├─ code={d2.get("code")}')
        proc = (d2.get('data') or {}).get('process') if d2.get('code') == 0 else None
        if proc:
            print(f'  ├─ order_no = {proc.get("order_no","?")}')
            print(f'  ├─ quantity = {proc.get("quantity","?")}')
            print(f'  ├─ completed_qty = {proc.get("completed_qty","(不存在)")}')
            print(f'  ├─ required_qty = {proc.get("required_qty","(不存在)")}')
            # 检查是否有步骤级别的数据
            steps = (d2.get('data') or {}).get('steps', [])
            print(f'  └─ steps = {len(steps)} 个')
            for si, s in enumerate(steps):
                print(f'     └─ step[{si}]: name={s.get("name","?")} status={s.get("status","?")}')
        else:
            print(f'  └─ 无 process 数据: {d2}')
    else:
        print(f'  └─ 错误: {d2}')

# ─── 3. 调度中心 sub_step_summary ──────────────────────────
print(f'\n【3】调度中心 /api/dispatch-center/process_sub_step_summary/<id>')
for p in items:
    pid = p.get('id','')
    if not pid or order not in p.get('order_no',''):
        continue
    d3 = fetch(f'{BASE}/api/dispatch-center/process_sub_step_summary/{pid}')
    print(f'  ├─ process_id={pid[:12]} step={p.get("step_name","?")}')
    if isinstance(d3, dict):
        print(f'  ├─ code={d3.get("code")} data={json.dumps(d3.get("data"), ensure_ascii=False, default=str)[:200]}')
    else:
        print(f'  └─ 结果: {str(d3)[:200]}')

# ─── 4. 报工系统 processes ────────────────────────────────
print(f'\n【4】报工系统 /api/processes（如果有此路由）')
# legacy_routes可能没有直接的processes路由，尝试多个路径
for path in ['/processes', '/api/processes', '/api/workorders']:
    d4 = fetch(f'{BASE}{path}')
    if not d4.get('_error'):
        print(f'  ├─ {path} → {type(d4).__name__}')
        if isinstance(d4, dict):
            items4 = d4.get('data') or []
            if isinstance(items4, list):
                for pp in items4:
                    if order in pp.get('order_no',''):
                        print(f'  │  └─ {pp.get("step_name","?")} cq={pp.get("completed_qty","?")} rq={pp.get("required_qty","?")}')
    else:
        print(f'  ├─ {path} → ❌ 404')

# ─── 5. 报工系统 sub_step_summary ─────────────────────────
print(f'\n【5】报工系统 /process_sub_step_summary/<order_no>（如果有此路由）')
try:
    r = urllib.request.urlopen(f'{BASE}/process_sub_step_summary/{order}', timeout=5)
    d5 = json.loads(r.read().decode())
    print(f'  响应: {json.dumps(d5, ensure_ascii=False, default=str)[:500]}')
except Exception as e:
    print(f'  ❌ {e}')

print('\n' + '=' * 65)
print('检查完成')
