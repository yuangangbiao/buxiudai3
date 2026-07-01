import os, json
f = os.path.join(os.path.dirname(__file__), 'enterprise_structure.json')
print(f'文件存在: {os.path.exists(f)}')
if os.path.exists(f):
    d = json.load(open(f, encoding='utf-8'))
    print(f'部门: {len(d.get("departments",[]))}, 用户: {len(d.get("users",[]))}')
    print(f'更新时间: {d.get("updated_at","")}')
else:
    print('文件不存在，需要同步')
