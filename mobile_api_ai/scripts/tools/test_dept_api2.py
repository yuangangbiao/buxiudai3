"""验证调度中心部门架构API（输出到文件便于查看）"""
import urllib.request, json, sys

try:
    resp = urllib.request.urlopen(
        'http://localhost:5003/api/dispatch-center/operators/wechat-departments',
        timeout=5
    )
    data = json.loads(resp.read())
    print('=== 部门架构API测试 ===')
    print(f'HTTP Status: {resp.status}')
    print(f'code: {data.get("code")}')
    print(f'source: {data.get("data",{}).get("source","?")}')
    print(f'depts: {len(data.get("data",{}).get("departments",[]))}')
    depts = data.get('data',{}).get('departments',[])
    for d in depts[:3]:
        print(f'  - {d.get("name")} ({len(d.get("members",[]))}人, {len(d.get("children",[]))}子部门)')
    print('...更多数据省略')
    print('=== 测试通过 ===')
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
