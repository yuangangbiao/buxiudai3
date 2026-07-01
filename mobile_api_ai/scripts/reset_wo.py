import json, os
cache_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dispatch_center_data.json')
with open(cache_file, 'r', encoding='utf-8') as f:
    data = json.load(f)
for p in data.get('processes', []):
    if p.get('order_no') == 'WO-202605005':
        print(f'重置: current_step={p["current_step"]} -> 0')
        p['current_step'] = 0
        p['status'] = 'pending'
        for k in ['awaiting_confirmation','awaiting_step','awaiting_step_status','awaiting_since','awaiting_operator',
                   'schedule_confirmed','schedule_confirmed_at','schedule_remark','lead_time','lead_time_unit']:
            p.pop(k, None)
        for k in list(p.keys()):
            if k.startswith('completed_'):
                p.pop(k, None)
        break
with open(cache_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print('完成')
