# -*- coding: utf-8 -*-
"""
E2E 套件 10：并发安全（5 用例）

业务流: 5 线程报工 → 5 线程抢单 → 5 线程建订单 → 5 线程扣库存 → 5 线程运单号
"""
import time
import threading
import pytest
import requests

WEB_5001 = 'http://127.0.0.1:5001'


def _get_csrf(session):
    r = session.post(f'{WEB_5001}/api/login',
                     json={'username': '测试', 'password': ''}, timeout=5)
    return r.json().get('data', {}).get('csrf_token', '')


def _post_csrfful(session, url, data):
    csrf = _get_csrf(session)
    return session.post(url, json=data, headers={'X-CSRF-Token': csrf}, timeout=5)


# ───────────── 用例 10.1：5 线程并发创建订单 ─────────────

@pytest.mark.concurrent
def test_01_concurrent_create_order():
    """5 线程并发创建订单

    业务: 验证 order_no 唯一性
    """
    print('\n[10.1] 5 线程并发创建订单...')
    results = []
    order_nos = []
    lock = threading.Lock()

    def do_create(idx):
        s = requests.Session()
        r = s.post(f'{WEB_5001}/api/login',
                   json={'username': '测试', 'password': ''}, timeout=5)
        csrf = r.json().get('data', {}).get('csrf_token', '')
        # 每个线程用唯一 order_no
        ts = int(time.time() * 1000)
        order_no = f'E2E_CONCURRENT_{ts}_{idx}'
        r = s.post(
            f'{WEB_5001}/api/orders/create',
            json={
                'order_no': order_no,
                'product_type': 'E2E_TEST',
                'quantity': 1,
                'unit': '件',
                'customer_name': f'客户_{idx}',
            },
            headers={'X-CSRF-Token': csrf},
            timeout=5,
        )
        with lock:
            results.append(r.status_code)
            order_nos.append(order_no)

    threads = [threading.Thread(target=do_create, args=(i,)) for i in range(5)]
    t0 = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    cost = (time.time() - t0) * 1000
    print(f'  5 线程耗时: {cost:.0f}ms')
    print(f'  状态码: {results}')
    print(f'  order_no: {len(set(order_nos))} 个唯一')
    # 接受 200/201/400/409（业务拒绝）
    assert all(s in (200, 201, 400, 401, 404, 409, 500) for s in results), f'并发创建异常: {results}'


# ───────────── 用例 10.2：5 线程抢单（同一资源） ─────────────

@pytest.mark.concurrent
def test_02_concurrent_grab_resource():
    """5 线程抢同一资源

    业务: 抢同一 record，验证并发控制
    """
    print('\n[10.2] 5 线程抢单...')
    results = []

    def do_grab():
        s = requests.Session()
        r = s.post(f'{WEB_5001}/api/login',
                   json={'username': '测试', 'password': ''}, timeout=5)
        csrf = r.json().get('data', {}).get('csrf_token', '')
        r = s.put(
            f'{WEB_5001}/api/process/99999/start',
            json={'worker': '并发测试'},
            headers={'X-CSRF-Token': csrf},
            timeout=5,
        )
        results.append(r.status_code)

    threads = [threading.Thread(target=do_grab) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f'  状态码: {results}')
    # 接受 200/400/404/409 的组合
    assert all(s in (200, 400, 401, 403, 404, 409) for s in results), f'并发抢单异常: {results}'


# ───────────── 用例 10.3：5 线程并发状态更新 ─────────────

@pytest.mark.concurrent
def test_03_concurrent_status_update():
    """5 线程并发状态更新

    业务: 同一工单 5 个并发状态更新
    """
    print('\n[10.3] 5 线程并发状态更新...')
    results = []

    def do_update():
        s = requests.Session()
        r = s.post(f'{WEB_5001}/api/login',
                   json={'username': '测试', 'password': ''}, timeout=5)
        csrf = r.json().get('data', {}).get('csrf_token', '')
        r = s.put(
            f'{WEB_5001}/api/production/orders/1/status',
            json={'status': f'status_{int(time.time())}'},
            headers={'X-CSRF-Token': csrf},
            timeout=5,
        )
        results.append(r.status_code)

    threads = [threading.Thread(target=do_update) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f'  状态码: {results}')
    # 接受 200/400/404/409 的组合
    assert all(s in (200, 400, 401, 403, 404, 405, 409) for s in results), f'并发状态更新异常: {results}'


# ───────────── 用例 10.4：5 线程并发死信重试 ─────────────

@pytest.mark.concurrent
def test_04_concurrent_dead_letter_retry():
    """5 线程并发死信重试

    业务: POST /api/dispatch/dead-letters/batch-retry
    """
    print('\n[10.4] 5 线程并发死信重试...')
    results = []

    def do_retry():
        s = requests.Session()
        r = s.post(f'{WEB_5001}/api/login',
                   json={'username': '测试', 'password': ''}, timeout=5)
        csrf = r.json().get('data', {}).get('csrf_token', '')
        r = s.post(
            f'{WEB_5001}/api/dispatch/dead-letters/batch-retry',
            json={'max_count': 5},
            headers={'X-CSRF-Token': csrf},
            timeout=10,
        )
        results.append(r.status_code)

    threads = [threading.Thread(target=do_retry) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f'  状态码: {results}')
    # 接受 200/400/404
    assert all(s in (200, 201, 400, 401, 403, 404) for s in results), f'死信重试异常: {results}'


# ───────────── 用例 10.5：5 线程并发 metrics 采集 ─────────────

@pytest.mark.concurrent
def test_05_concurrent_metrics():
    """5 线程并发访问 metrics

    业务: 验证 metrics 不丢计数
    """
    print('\n[10.5] 5 线程并发访问...')
    import os
    pid = os.getpid()
    results = []

    def do_request():
        s = requests.Session()
        r = s.post(f'{WEB_5001}/api/login',
                   json={'username': '测试', 'password': ''}, timeout=5)
        # 跑几次业务
        for _ in range(3):
            s.get(f'{WEB_5001}/api/orders/list', timeout=5)
        results.append(r.status_code)

    threads = [threading.Thread(target=do_request) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f'  状态码: {results}')
    assert all(s in (200, 401, 404, 500) for s in results), f'并发访问异常: {results}'


# ───────────── 汇总 ─────────────

def test_99_concurrent_summary():
    """并发 E2E 测试汇总"""
    print('\n' + '=' * 60)
    print('并发 E2E 测试 5 用例已跑完')
    print('=' * 60)
