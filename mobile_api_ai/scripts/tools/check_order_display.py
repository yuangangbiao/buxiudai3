# -*- coding: utf-8 -*-
"""检查 ORD-202604210002 在 all-process-tasks API 返回的数据"""
import json, sys
sys.path.insert(0, 'd:/yuan/不锈钢网带跟单3.0/mobile_api_ai')
from container_center_v5 import ContainerCenter

cc = ContainerCenter()
all_records = cc.storage.get_all_process_records()

# 找到目标订单
target = None
for rec in all_records:
    if rec.get('order_no') == 'ORD-202604210002':
        target = rec
        break

if not target:
    print("ERROR: 未找到 ORD-202604210002")
    sys.exit(1)

print("=== process_records 原始数据 ===")
for k, v in target.items():
    val_str = repr(v)
    if len(val_str) > 300:
        val_str = val_str[:300] + '...'
    print(f'  {k}: {val_str}')

# 检查字段长度
print("\n=== 字段长度检查 ===")
for field in ['product_name', 'customer_group', 'customer_name', 'order_no']:
    val = target.get(field, '')
    print(f'  {field}: len={len(str(val))}, value={repr(val)[:100]}')

# 检查 steps
steps_raw = target.get('steps', []) or []
if isinstance(steps_raw, str):
    import json as _j
    steps_raw = _j.loads(steps_raw) if steps_raw else []
print(f'\n  steps: len={len(steps_raw)}')

# 检查子步骤
sub_steps = cc.get_sub_steps('ORD-202604210002')
print(f'\n  sub_steps: {len(sub_steps)} 条')
for ss in sub_steps[:10]:
    print(f'    step_name={ss.get("step_name")} quantity={ss.get("quantity")}')
if len(sub_steps) > 10:
    print(f'    ... 还有 {len(sub_steps)-10} 条')

# 模拟 API 返回数据
print("\n=== API 返回模拟 ===")
step_completed = {}
for ss in sub_steps:
    sn = ss.get('step_name', '')
    step_completed[sn] = step_completed.get(sn, 0) + float(ss.get('quantity', 0) or 0)

processes = []
for i, si in enumerate(steps_raw):
    si_name = si.get('name', '') if isinstance(si, dict) else str(si)
    si_rq = float(si.get('required_qty', 0) or 0) if isinstance(si, dict) else 0
    completed = step_completed.get(si_name, 0)
    remaining = max(0, si_rq - completed)
    status = 'done' if completed >= si_rq > 0 else ('doing' if completed > 0 else 'wait')
    processes.append({
        'process_id': i,
        'process_name': si_name,
        'required_qty': si_rq,
        'completed_qty': completed,
        'remaining_qty': remaining,
        'status': status,
    })

result = {
    'order_no': target.get('order_no', ''),
    'product_name': target.get('product_name', ''),
    'customer_group': target.get('customer_group', '') or target.get('customer_name', ''),
    'quantity': float(target.get('quantity', 0) or 0),
    'unit': target.get('unit', ''),
    'total_completed_qty': sum(step_completed.values()),
    'total_remaining_qty': max(0, float(target.get('quantity', 0) or 0) - sum(step_completed.values())),
    'processes': processes,
}

print(json.dumps(result, ensure_ascii=False, indent=2))
