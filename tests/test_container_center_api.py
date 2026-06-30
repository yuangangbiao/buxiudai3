"""test_container_center_api.py - 直接 import 测覆盖率（Flask test client）

HTTP 测试覆盖不了模块内的代码路径（跨进程）。
改用 Flask test_client 直接 import + 调用，收集真实覆盖率。

[修复 2026-06-14] container_center_api 懒导入，避免在 pytest 收集阶段
污染 sys.path，导致其他 tests/unit/ 文件的 "from core.xxx import" 失败。
"""
import sys, os

_SELF_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJ_ROOT = os.path.dirname(_SELF_DIR)  # tests/ → 项目根
sys.path.insert(0, os.path.join(_PROJ_ROOT, 'mobile_api_ai'))

os.environ['API_KEY'] = 'test-api-key-12345'
os.environ['WECHAT_CLOUD_API_KEY'] = 'test-api-key-12345'
os.environ['MYSQL_HOST'] = '127.0.0.1'
os.environ['MYSQL_PORT'] = '3306'
os.environ['MYSQL_USER'] = 'root'
os.environ['MYSQL_PASSWORD'] = '88888888'
os.environ['MYSQL_DATABASE'] = 'container_center'

import pytest

_cached_app = None

def _get_app():
    global _cached_app
    if _cached_app is None:
        from container_center_api import app as _app
        _cached_app = _app
    return _cached_app

@pytest.fixture
def client():
    app = _get_app()
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c

def test_health(client):
    r = client.get('/api/health')
    assert r.status_code == 200

def test_pool_status(client):
    r = client.get('/api/pool/status', headers={'X-API-Key': 'test-api-key-12345'})
    assert r.status_code == 200

def test_get_sub_steps(client):
    r = client.get('/api/process_sub_steps/ORD-20260416-0001',
                   headers={'X-API-Key': 'test-api-key-12345'})
    assert r.status_code == 200
    j = r.get_json()
    assert j.get('code') == 0

def test_get_sub_step_summary(client):
    r = client.get('/api/process_sub_step_summary/ORD-20260416-0001',
                   headers={'X-API-Key': 'test-api-key-12345'})
    assert r.status_code == 200
    j = r.get_json()
    assert j.get('code') == 0

def test_create_substep_success(client):
    import uuid
    r = client.post('/api/process_sub_step',
        json={'order_no': 'ORD-20260416-0001', 'step_name': '入库',
              'quantity': 1, 'operator': 'coveragetest'},
        headers={'X-API-Key': 'test-api-key-12345'})
    assert r.status_code == 200
    j = r.get_json()
    assert j.get('code') == 0, f'期望成功，实际{j}'

def test_create_substep_invalid_quantity(client):
    r = client.post('/api/process_sub_step',
        json={'order_no': 'ORD-20260416-0001', 'step_name': '入库',
              'quantity': -5, 'operator': 'test'},
        headers={'X-API-Key': 'test-api-key-12345'})
    assert r.status_code == 200
    j = r.get_json()
    assert j.get('code') != 0

def test_create_substep_bad_step_name(client):
    r = client.post('/api/process_sub_step',
        json={'order_no': 'ORD-20260416-0001', 'step_name': '非法工序',
              'quantity': 1, 'operator': 'test'},
        headers={'X-API-Key': 'test-api-key-12345'})
    assert r.status_code == 200
    j = r.get_json()
    assert j.get('code') != 0

def test_create_substep_missing_body(client):
    r = client.post('/api/process_sub_step',
        headers={'X-API-Key': 'test-api-key-12345'},
        content_type='application/json')
    assert r.status_code == 200
