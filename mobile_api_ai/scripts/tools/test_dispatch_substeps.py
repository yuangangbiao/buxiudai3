"""测试调度中心子步骤 API"""
import urllib.request, json, sys
sys.stdout.reconfigure(encoding='utf-8')

BASE = 'http://127.0.0.1:5008'
order = 'ORD-202604290001'
process_id = 'f44f2f00-5629-4d5c-9b91-77457294781e'

# 1. process_sub_step_summary
print('=== process_sub_step_summary (调度中心) ===')
try:
    r = urllib.request.urlopen(f'{BASE}/api/dispatch-center/process_sub_step_summary/{process_id}', timeout=5)
    data = json.loads(r.read().decode())
    print(json.dumps(data, ensure_ascii=False, indent=2)[:500])
except Exception as e:
    print(f'❌ {e}')

# 2. process_sub_steps
print('\n=== process_sub_steps (调度中心) ===')
try:
    r = urllib.request.urlopen(f'{BASE}/api/dispatch-center/process_sub_steps/{process_id}', timeout=5)
    data = json.loads(r.read().decode())
    print(json.dumps(data, ensure_ascii=False, indent=2)[:500])
except Exception as e:
    print(f'❌ {e}')

# 3. process detail (看500错误是否修复)
print('\n=== process detail ===')
try:
    r = urllib.request.urlopen(f'{BASE}/api/dispatch-center/processes/{process_id}', timeout=5)
    data = json.loads(r.read().decode())
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str)[:500])
except Exception as e:
    print(f'❌ {e}')

print('\n完成')
