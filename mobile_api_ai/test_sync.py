"""测试容器中心同步"""
import requests, os, json

r = requests.post('http://127.0.0.1:5002/api/enterprise/structure/sync', timeout=30)
print(f'HTTP {r.status_code}')
d = r.json()
print(f'code={d.get("code")}, msg={d.get("message")}')

if d.get('code') == 0:
    data = d.get('data', {})
    print(f'同步成功: {len(data.get("departments",[]))} 部门, {len(data.get("users",[]))} 用户')
    # 验证本地文件
    fp = os.path.join(os.path.dirname(__file__), 'enterprise_structure.json')
    if os.path.exists(fp):
        ld = json.load(open(fp, encoding='utf-8'))
        print(f'本地文件: {len(ld.get("departments",[]))} 部门, {len(ld.get("users",[]))} 用户')
    else:
        print('本地文件不存在')
else:
    print('同步失败')
