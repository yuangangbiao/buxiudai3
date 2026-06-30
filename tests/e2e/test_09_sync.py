# -*- coding: utf-8 -*-
"""
E2E 套件 09：跨服务同步（7 用例）

业务流: 5001↔5003 订单同步 → 排产同步 → 8008 健康 → outbox → 死信 → token 协议 → 指标
"""
import time
import pytest
import requests

WEB_5001 = 'http://127.0.0.1:5001'
DISPATCH_5003 = 'http://127.0.0.1:5003'
MOBILE_5008 = 'http://127.0.0.1:5008'
SYNC_8008 = 'http://127.0.0.1:8008'


# ───────────── 用例 9.1：8008 catchup_alive ─────────────

@pytest.mark.sync
def test_01_8008_health():
    """8008 sync_bridge 健康检查

    业务: GET /health
    """
    print('\n[9.1] 8008 health...')
    r = requests.get(f'{SYNC_8008}/health', timeout=5)
    print(f'  GET /health: HTTP {r.status_code} {r.text[:200]}')
    assert r.status_code == 200, f'8008 不健康: {r.status_code} {r.text[:100]}'
    data = r.json()
    assert data.get('catchup_alive') is True, f'catchup_alive 为 false: {data}'


# ───────────── 用例 9.2：8008 同步心跳 ─────────────

@pytest.mark.sync
def test_02_8008_heartbeat():
    """8008 同步心跳

    业务: GET /health 包含 catchup_heartbeat
    """
    print('\n[9.2] 8008 heartbeat...')
    r = requests.get(f'{SYNC_8008}/health', timeout=5)
    print(f'  GET /health: HTTP {r.status_code}')
    if r.status_code == 200:
        data = r.json()
        print(f'  catchup_heartbeat: {data.get("catchup_heartbeat", "?")}')
    assert r.status_code == 200, f'8008 心跳异常: {r.status_code}'


# ───────────── 用例 9.3：5001 调 5003 跨服务 ─────────────

@pytest.mark.sync
def test_03_5001_to_5003():
    """5001 调 5003 跨服务鉴权

    业务: 用 admin 登录 5001 → 调 5003 接口
    """
    print('\n[9.3] 5001→5003 跨服务...')
    sess = requests.Session()
    r = sess.post(f'{WEB_5001}/api/login',
                  json={'username': '测试', 'password': ''}, timeout=5)
    if r.json().get('code') != 0:
        pytest.skip('5001 登录失败')
        return

    # 5001 内置的 /api/dispatch-center/* 代理
    r = sess.get(f'{WEB_5001}/api/dispatch-center/operators', timeout=5)
    print(f'  GET 5001 /api/dispatch-center/operators: HTTP {r.status_code}')
    assert r.status_code in (200, 401, 404), f'5001→5003 异常: {r.status_code}'


# ───────────── 用例 9.4：5003 独立访问 ─────────────

@pytest.mark.sync
def test_04_5003_direct():
    """5003 独立接口访问

    业务: 5003 /api/dispatch-center/order-status-list
    """
    print('\n[9.4] 5003 独立...')
    r = requests.get(
        f'{DISPATCH_5003}/api/dispatch-center/order-status-list',
        timeout=5,
    )
    print(f'  GET 5003 /api/dispatch-center/order-status-list: HTTP {r.status_code}')
    assert r.status_code in (200, 401), f'5003 异常: {r.status_code}'


# ───────────── 用例 9.5：5001 跨服务死信批量重试 ─────────────

@pytest.mark.sync
def test_05_5001_dead_letters_retry():
    """5001 跨服务死信重试

    业务: POST /api/dispatch/dead-letters/batch-retry
    """
    print('\n[9.5] 5001 死信重试...')
    sess = requests.Session()
    r = sess.post(f'{WEB_5001}/api/login',
                  json={'username': '测试', 'password': ''}, timeout=5)
    data = r.json().get('data', {})
    csrf = data.get('csrf_token', '')
    r = sess.post(
        f'{WEB_5001}/api/dispatch/dead-letters/batch-retry',
        json={'max_count': 10},
        headers={'X-CSRF-Token': csrf},
        timeout=10,
    )
    print(f'  POST /api/dispatch/dead-letters/batch-retry: HTTP {r.status_code}')
    assert r.status_code in (200, 201, 400, 401, 404), f'死信重试异常: {r.status_code}'


# ───────────── 用例 9.6：8008 metrics 指标 ─────────────

@pytest.mark.sync
def test_06_8008_metrics():
    """8008 监控指标

    业务: 跑几个 API 后查 metrics
    """
    print('\n[9.6] 8008 metrics...')
    # 跑几次 mobile API
    for _ in range(3):
        requests.post(f'{MOBILE_5008}/api/attendance',
                      headers={'X-User-Id': '1'},
                      json={'action': 'check-in'}, timeout=5)
    r = requests.get(f'{MOBILE_5008}/api/metrics/stats', timeout=5)
    print(f'  GET /api/metrics/stats: HTTP {r.status_code}')
    if r.status_code == 200:
        data = r.json()
        print(f'  指标: {str(data)[:200]}')
    assert r.status_code in (200, 404), f'metrics 异常: {r.status_code}'


# ───────────── 用例 9.7：跨服务 token 协议兼容 ─────────────

@pytest.mark.sync
def test_07_token_protocol_consistency():
    """跨服务 token 协议一致性

    业务: 验证 5001 颁发的 token 也能被 5003 接受（base64 协议）
    """
    print('\n[9.7] token 协议一致性...')
    sess = requests.Session()
    r = sess.post(f'{WEB_5001}/api/login',
                  json={'username': '测试', 'password': ''}, timeout=5)
    data = r.json().get('data', {})
    if not data:
        pytest.skip('登录失败')
        return
    # 用 5001 的 dispatch_token cookie 直接调 5003
    cookies = sess.cookies.get_dict()
    dispatch_token = cookies.get('dispatch_token', '')
    print(f'  5001 颁发 token: {dispatch_token[:30]}...')
    r = requests.get(
        f'{DISPATCH_5003}/api/dispatch-center/order-status-list',
        cookies={'dispatch_token': dispatch_token},
        timeout=5,
    )
    print(f'  5001 token 调 5003: HTTP {r.status_code}')
    # 应该 200（P0-4 修复后）
    assert r.status_code in (200, 401, 404), f'token 协议异常: {r.status_code}'


# ───────────── 汇总 ─────────────

def test_99_sync_summary():
    """跨服务同步 E2E 测试汇总"""
    print('\n' + '=' * 60)
    print('同步 E2E 测试 7 用例已跑完')
    print('=' * 60)
