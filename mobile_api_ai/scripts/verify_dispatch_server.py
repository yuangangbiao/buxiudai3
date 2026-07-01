import urllib.request
import json

BASE = 'http://127.0.0.1:5003'
passed = 0
failed = 0

def test(name, url, expect_code=0, expect_http=200, method='GET', data=None):
    global passed, failed
    try:
        req = urllib.request.Request(url, method=method, data=data)
        r = urllib.request.urlopen(req, timeout=5)
        body = r.read()
        http_ok = r.status == expect_http
        code_ok = True
        if body and expect_code is not None:
            d = json.loads(body)
            code_ok = d.get('code') == expect_code
        elif not body:
            code_ok = expect_code is None
        status = 'PASS' if (http_ok and code_ok) else 'FAIL'
        if status == 'PASS':
            passed += 1
        else:
            failed += 1
        info = f'HTTP {r.status}'
        if body:
            d = json.loads(body)
            info += f', code={d.get("code")}'
        print(f'  [{status}] {name}: {info}')
        if status == 'FAIL' and body:
            print(f'          {json.dumps(json.loads(body), ensure_ascii=False)[:200]}')
    except urllib.error.HTTPError as e:
        body = e.read()
        code_ok = True
        if body and expect_code is not None:
            d = json.loads(body)
            code_ok = d.get('code') == expect_code
        elif not body:
            code_ok = expect_code is None
        http_ok = e.code == expect_http
        status = 'PASS' if (http_ok and code_ok) else 'FAIL'
        if status == 'PASS':
            passed += 1
        else:
            failed += 1
        info = f'HTTP {e.code}'
        if body:
            d = json.loads(body)
            info += f', code={d.get("code")}'
        print(f'  [{status}] {name}: {info}')
        if status == 'FAIL' and body:
            print(f'          {json.dumps(json.loads(body), ensure_ascii=False)[:200]}')
    except Exception as e:
        failed += 1
        print(f'  [FAIL] {name}: {e}')

print('=' * 60)
print('  调度中心服务器 (5003) 修复验证')
print('=' * 60)

print('\n[1/5] 基础功能')
test('健康检查(含线程监控)', f'{BASE}/health')
test('不存在的路由(404处理器)', f'{BASE}/api/nonexistent', expect_code=404, expect_http=404)
test('favicon(204空体)', f'{BASE}/favicon.ico', expect_code=None, expect_http=204)

print('\n[2/5] 企业架构API (P0-锁一致性)')
test('获取架构(GET)', f'{BASE}/api/enterprise/structure')
test('保存架构(POST空数据)', f'{BASE}/api/enterprise/structure', expect_code=1, method='POST', data=json.dumps({}).encode())

print('\n[3/5] 调度中心业务API')
test('调度看板', f'{BASE}/api/dispatch-center/status')

print('\n[4/5] 后台线程健康')
r = urllib.request.urlopen(f'{BASE}/health', timeout=5)
d = json.loads(r.read())
threads = d.get('threads', {})
print(f'  [INFO] 线程状态: {json.dumps(threads, ensure_ascii=False)}')
if threads.get('cost_checker') == 'alive' or threads.get('alert_engine') == 'alive':
    passed += 1
    print(f'  [PASS] 后台线程存活')
else:
    failed += 1
    print(f'  [FAIL] 后台线程异常')

print(f'\n{"=" * 60}')
print(f'  结果: {passed} passed, {failed} failed / {passed + failed} total')
print(f'{"=" * 60}')
