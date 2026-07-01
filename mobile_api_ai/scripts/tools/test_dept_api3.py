"""测试 wechat-departments API（避免shell转义问题）"""
import urllib.request, json, sys

try:
    resp = urllib.request.urlopen(
        'http://localhost:5003/api/dispatch-center/operators/wechat-departments',
        timeout=15
    )
    print('HTTP status:', resp.status)
    raw = resp.read()
    print('Response length:', len(raw))
    data = json.loads(raw)
    print('code:', data.get('code'))
    print('message:', data.get('message', ''))
    dd = data.get('data', {})
    print('source:', dd.get('source', '?'))
    depts = dd.get('departments', [])
    print('departments count:', len(depts))
    if depts:
        for d in depts[:5]:
            children = d.get('children', [])
            members = d.get('members', [])
            print(f'  dept: {d.get("name","?")} (id={d.get("id")}, members={len(members)}, children={len(children)})')
    print('SUCCESS')
except Exception as e:
    print(f'ERROR: {type(e).__name__}: {e}')
    sys.exit(1)
