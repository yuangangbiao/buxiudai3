"""验证企业架构数据 (F16 T16.3 修复)
[F6 P9 兼容] enterprise_structure 表已 DROP, 改读 data/enterprise_structure.json
"""
import json
import os

# 优先项目根 data/, 兼容 storage/data/
candidates = [
    os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'enterprise_structure.json'),
    os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'enterprise_structure.json'),
]
data = None
for p in candidates:
    p = os.path.normpath(p)
    if os.path.exists(p):
        try:
            with open(p, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f'[F16 T16.3] 读 {p}')
            break
        except Exception as e:
            print(f'[F16 T16.3] 读 {p} 失败: {e}')

if not data:
    print('ERROR: 未找到 data/enterprise_structure.json')
    raise SystemExit(1)

depts = data.get('departments', [])
users = data.get('users', [])
updated = data.get('updated_at', '')

print(f'JSON 状态: {len(depts)} 个部门, {len(users)} 名用户')
print(f'更新时间: {updated}')
print()
print('部门列表:')
for d in depts:
    if isinstance(d, dict):
        print(f'  [{d.get("id")}] {d.get("name")} (parentid={d.get("parentid")})')
print()
print(f'用户列表 ({len(users)}):')
for u in users:
    if isinstance(u, dict):
        print(f'  {u.get("name")} ({u.get("userid")}) -> dept={u.get("department", [])}')
