#!/usr/bin/env python
"""测试 process API 三条路由"""
import json
import urllib.request
import urllib.error

BASE = 'http://localhost:5008/api/process'


def test(path, method='GET', data=None):
    url = BASE + path
    if data:
        req = urllib.request.Request(url, data=json.dumps(data).encode(), method=method)
        req.add_header('Content-Type', 'application/json')
    else:
        req = urllib.request.Request(url, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())


if __name__ == '__main__':
    # 1. my-tasks
    r = test('/my-tasks?worker_id=OP001')
    print('=== my-tasks ===')
    print(json.dumps(r, indent=2, ensure_ascii=False))

    # 2. history
    r = test('/history?worker_id=OP001')
    print('\n=== history ===')
    print(json.dumps(r, indent=2, ensure_ascii=False))

    # 3. report
    r = test('/101/report', 'POST', {'completed_qty': 100, 'status': '已完成', 'device_remark': '测试报工'})
    print('\n=== report(101) ===')
    print(json.dumps(r, indent=2, ensure_ascii=False))
