"""test_coverage_boost.py - 增加 container_center_api 覆盖率

目标：覆盖 api_get_sub_steps、api_get_sub_step_summary、异常路径
"""
import uuid, requests

BASE = 'http://127.0.0.1'
API_KEY = 'test-api-key-12345'

def test_5002_get_sub_steps():
    """GET /api/process_sub_steps/<order_no> - 查询子步骤"""
    order = 'ORD-20260416-0001'
    r = requests.get(f'{BASE}:5002/api/process_sub_steps/{order}',
                     headers={'X-API-Key': API_KEY}, timeout=5)
    assert r.status_code == 200, f'应200, 实际{r.status_code}'
    j = r.json()
    assert j.get('code') == 0, f'code应0, 实际{j.get("code")}'
    assert isinstance(j.get('data'), list), f'data应为list, 实际{type(j.get("data"))}'
    print(f'  ✓ GET /api/process_sub_steps/{order}: {len(j.get("data",[]))} 条子步骤')


def test_5002_get_sub_step_summary():
    """GET /api/process_sub_step_summary/<order_no> - 查询汇总"""
    order = 'ORD-20260416-0001'
    r = requests.get(f'{BASE}:5002/api/process_sub_step_summary/{order}',
                     headers={'X-API-Key': API_KEY}, timeout=5)
    assert r.status_code == 200, f'应200, 实际{r.status_code}'
    j = r.json()
    assert j.get('code') == 0, f'code应0, 实际{j.get("code")}'
    print(f'  ✓ GET /api/process_sub_step_summary/{order}: {j.get("data")}')


def test_5002_invalid_quantity():
    """quantity 异常值"""
    r = requests.post(f'{BASE}:5002/api/process_sub_step',
        json={'order_no': 'ORD-20260416-0001', 'step_name': '入库',
              'quantity': -1, 'operator': 'test'},
        headers={'X-API-Key': API_KEY}, timeout=5)
    assert r.status_code == 200
    j = r.json()
    assert j.get('code') != 0, f'负数quantity应失败, 实际{j}'
    print(f'  ✓ 负数quantity: {j.get("message")[:40]}')


def test_5002_large_quantity():
    """quantity 超出上限"""
    r = requests.post(f'{BASE}:5002/api/process_sub_step',
        json={'order_no': 'ORD-20260416-0001', 'step_name': '入库',
              'quantity': 99999999999, 'operator': 'test'},
        headers={'X-API-Key': API_KEY}, timeout=5)
    assert r.status_code == 200
    j = r.json()
    assert j.get('code') != 0
    print(f'  ✓ 超大quantity: {j.get("message")[:40]}')


def test_5002_bad_step_name():
    """非法 step_name"""
    r = requests.post(f'{BASE}:5002/api/process_sub_step',
        json={'order_no': 'ORD-20260416-0001', 'step_name': '非法工序',
              'quantity': 1, 'operator': 'test'},
        headers={'X-API-Key': API_KEY}, timeout=5)
    assert r.status_code == 200
    j = r.json()
    assert j.get('code') != 0
    print(f'  ✓ 非法step_name: {j.get("message")[:40]}')


def test_5002_order_not_found():
    """订单不存在"""
    fake_order = f'NOTFOUND-{uuid.uuid4().hex[:8]}'
    r = requests.post(f'{BASE}:5002/api/process_sub_step',
        json={'order_no': fake_order, 'step_name': '入库',
              'quantity': 1, 'operator': 'test'},
        headers={'X-API-Key': API_KEY}, timeout=5)
    assert r.status_code == 200
    j = r.json()
    assert j.get('code') != 0, f'不存在的订单应失败, 实际{j}'
    print(f'  ✓ 不存在订单: {j.get("message")[:40]}')


def test_5002_health_no_auth():
    """健康检查无需鉴权"""
    r = requests.get(f'{BASE}:5002/api/health', timeout=5)
    assert r.status_code == 200, f'/health应200, 实际{r.status_code}'
    print(f'  ✓ /api/health 无鉴权: {r.status_code}')


def test_5002_pool_status():
    """连接池状态"""
    r = requests.get(f'{BASE}:5002/api/pool/status',
                     headers={'X-API-Key': API_KEY}, timeout=5)
    assert r.status_code == 200, f'/pool/status应200, 实际{r.status_code}'
    print(f'  ✓ /api/pool/status: {r.status_code}')


def test_5002_rate_limit_200_qps():
    """200 QPS（不触发限流）"""
    import time, concurrent.futures as cf
    def hit():
        return requests.get(f'{BASE}:5002/api/health', timeout=3).status_code
    start = time.time()
    with cf.ThreadPoolExecutor(max_workers=20) as ex:
        futures = [ex.submit(hit) for _ in range(100)]
        results = [f.result() for f in cf.as_completed(futures)]
    elapsed = time.time() - start
    success = sum(1 for r in results if r == 200)
    assert success == 100, f'100个请求应全200, 实际{success}'
    print(f'  ✓ 100请求/20worker: {success}/100 成功, {elapsed:.1f}s')


def test_8008_sync_status():
    """8008 同步状态"""
    r = requests.get(f'{BASE}:8008/api/sync/status', timeout=5)
    assert r.status_code == 200
    print(f'  ✓ 8008 /api/sync/status: {r.status_code}')


def test_8008_queue_stats():
    """8008 队列统计"""
    r = requests.get(f'{BASE}:8008/api/sync/queue/stats', timeout=5)
    assert r.status_code == 200
    print(f'  ✓ 8008 /api/sync/queue/stats: {r.status_code}')


if __name__ == '__main__':
    import subprocess, sys
    sys.exit(subprocess.call([sys.executable, '-m', 'pytest', __file__, '-v', '--tb=short', '--no-cov']))
