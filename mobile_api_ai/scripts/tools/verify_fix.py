"""验证dispatch center修复效果的脚本"""
import sys, json, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from storage_layer import StorageLayer

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
db_path = os.path.join(project_root, 'wechat_container.db')
print(f'DB path: {db_path}')
print(f'DB exists: {os.path.exists(db_path)}')
print(f'DB size: {os.path.getsize(db_path)} bytes')

store = StorageLayer({'type': 'sqlite', 'db_path': db_path})

process_id = 'f44f2f00-5629-4d5c-9b91-77457294781e'

steps = store.get_sub_steps_by_process(process_id)
print(f'\nSub steps count: {len(steps)}')
for s in steps:
    print(f'  {s["step_name"]} qty={s["quantity"]} batch={s.get("batch_no","")} time={s["created_at"]}')

summary = store.get_sub_step_summary(process_id)
print(f'\nSummary (after fix): {json.dumps(summary, ensure_ascii=False)}')
