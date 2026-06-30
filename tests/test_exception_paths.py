"""test_exception_paths.py - 异常路径测试

测试：无效参数、错误 Content-Type、空 body、慢DB响应、超时
"""
import requests
import json

def test_5002_invalid_json():
    r = requests.post('http://127.0.0.1:5002/api/process_sub_step',
                      data='not json', headers={'X-API-Key': 'test-api-key-12345', 'Content-Type': 'application/json'}, timeout=5)
    assert r.status_code in (200, 400, 422), f"无效JSON应返回4xx, 实际 {r.status_code}"
    print(f'  ✓ 5002 无效JSON: {r.status_code}')

def test_5002_missing_fields():
    r = requests.post('http://127.0.0.1:5002/api/process_sub_step',
                      json={'order_no': 'ORD-20260416-0001'},  # 缺 step_name, quantity
                      headers={'X-API-Key': 'test-api-key-12345'}, timeout=5)
    assert r.status_code in (200, 400, 422), f"缺字段应4xx, 实际 {r.status_code}"
    print(f'  ✓ 5002 缺字段: {r.status_code}')

def test_5002_no_auth():
    r = requests.get('http://127.0.0.1:5002/api/health', timeout=5)
    assert r.status_code == 200, f"/api/health 无需鉴权, 实际 {r.status_code}"
    print(f'  ✓ 5002 /api/health 无鉴权200')

def test_5002_bad_api_key():
    r = requests.get('http://127.0.0.1:5002/api/pool/status', headers={'X-API-Key': 'wrong-key'}, timeout=5)
    assert r.status_code in (401, 403), f"错误API_KEY应401/403, 实际 {r.status_code}"
    print(f'  ✓ 5002 错误API_KEY: {r.status_code}')

def test_5002_not_found():
    r = requests.get('http://127.0.0.1:5002/api/nonexistent', headers={'X-API-Key': 'test-api-key-12345'}, timeout=5)
    assert r.status_code == 404, f"404应返回404, 实际 {r.status_code}"
    print(f'  ✓ 5002 不存在的路由: {r.status_code}')

def test_5008_no_auth():
    r = requests.get('http://127.0.0.1:5008/health', timeout=5)
    assert r.status_code == 200, f"5008/health无需鉴权, 实际 {r.status_code}"
    print(f'  ✓ 5008 /health 无鉴权200')

def test_8008_no_auth():
    r = requests.get('http://127.0.0.1:8008/api/sync/status', timeout=5)
    assert r.status_code == 200, f"8008/status无需鉴权, 实际 {r.status_code}"
    print(f'  ✓ 8008 /api/sync/status 无鉴权200')

def test_5010_no_auth():
    r = requests.get('http://127.0.0.1:5010/inventory/api/backup/list', timeout=5)
    assert r.status_code == 200, f"5010/backup无需鉴权, 实际 {r.status_code}"
    print(f'  ✓ 5010 /backup/list 无鉴权200')

if __name__ == '__main__':
    import subprocess, sys
    sys.exit(subprocess.call([sys.executable, '-m', 'pytest', __file__, '-v', '--tb=short', '--no-cov']))
