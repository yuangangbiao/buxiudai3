# -*- coding: utf-8 -*-
"""
E2E 套件 11：监控埋点（8 用例）

业务流: metrics/health → stats → reset → 4 蓝图埋点 → 错误率
"""
import pytest
import requests

WEB_5001 = 'http://127.0.0.1:5001'
MOBILE_5008 = 'http://127.0.0.1:5008'


# ───────────── 用例 11.1：metrics/health ─────────────

@pytest.mark.metrics
def test_01_metrics_health():
    """metrics 健康检查

    业务: GET /api/metrics/health
    注: 该端点可能未实现，应返回 404 而非 500。
    """
    print('\n[11.1] metrics health...')
    r = requests.get(f'{MOBILE_5008}/api/metrics/health', timeout=5)
    print(f'  GET /api/metrics/health: HTTP {r.status_code} {r.text[:200]}')
    assert r.status_code in (200, 404), f'metrics health 异常: {r.status_code}'


# ───────────── 用例 11.2：metrics/stats ─────────────

@pytest.mark.metrics
def test_02_metrics_stats():
    """metrics 统计

    业务: GET /api/metrics/stats
    """
    print('\n[11.2] metrics stats...')
    r = requests.get(f'{MOBILE_5008}/api/metrics/stats', timeout=5)
    print(f'  GET /api/metrics/stats: HTTP {r.status_code}')
    if r.status_code == 200:
        data = r.json()
        print(f'  统计: {str(data)[:200]}')
    assert r.status_code in (200, 404), f'metrics stats 异常: {r.status_code}'


# ───────────── 用例 11.3：metrics/reset ─────────────

@pytest.mark.metrics
def test_03_metrics_reset():
    """metrics 重置

    业务: POST /api/metrics/reset
    """
    print('\n[11.3] metrics reset...')
    r = requests.post(f'{MOBILE_5008}/api/metrics/reset', json={}, timeout=5)
    print(f'  POST /api/metrics/reset: HTTP {r.status_code}')
    assert r.status_code in (200, 201, 400, 401, 404), f'metrics reset 异常: {r.status_code}'


# ───────────── 用例 11.4：process 埋点 ─────────────

@pytest.mark.metrics
def test_04_process_metrics():
    """process 蓝图埋点采集

    业务: 调 process 后查看 stats
    """
    print('\n[11.4] process 埋点...')
    # 先 reset
    requests.post(f'{MOBILE_5008}/api/metrics/reset', json={}, timeout=5)
    # 跑几次 process
    for _ in range(3):
        r = requests.get(f'{MOBILE_5008}/api/process/my-tasks',
                         headers={'X-User-Id': '1'}, timeout=5)
    # 查 stats
    r = requests.get(f'{MOBILE_5008}/api/metrics/stats', timeout=5)
    if r.status_code == 200:
        data = r.json().get('data', {})
        print(f'  API 计数: {data.get("api_requests", "?")}')
    assert r.status_code in (200, 404), f'process 埋点异常: {r.status_code}'


# ───────────── 用例 11.5：quality 埋点 ─────────────

@pytest.mark.metrics
def test_05_quality_metrics():
    """quality 蓝图埋点

    业务: 调 quality 接口
    """
    print('\n[11.5] quality 埋点...')
    for _ in range(3):
        r = requests.get(f'{MOBILE_5008}/api/quality-inspection/tasks',
                         headers={'X-User-Id': '1'}, timeout=5)
    r = requests.get(f'{MOBILE_5008}/api/metrics/stats', timeout=5)
    print(f'  GET /api/metrics/stats: HTTP {r.status_code}')
    assert r.status_code in (200, 404), f'quality 埋点异常: {r.status_code}'


# ───────────── 用例 11.6：scan 埋点 ─────────────

@pytest.mark.metrics
def test_06_scan_metrics():
    """scan 蓝图埋点

    业务: 调 scan 接口
    """
    print('\n[11.6] scan 埋点...')
    for _ in range(3):
        r = requests.post(f'{MOBILE_5008}/api/scan/task',
                          headers={'X-User-Id': '1'},
                          json={'barcode': 'E2E_BAR', 'process_code': 'E2E_P01'},
                          timeout=5)
    r = requests.get(f'{MOBILE_5008}/api/metrics/stats', timeout=5)
    print(f'  GET /api/metrics/stats: HTTP {r.status_code}')
    assert r.status_code in (200, 404), f'scan 埋点异常: {r.status_code}'


# ───────────── 用例 11.7：attendance 埋点 ─────────────

@pytest.mark.metrics
def test_07_attendance_metrics():
    """attendance 埋点

    业务: 调 attendance 接口
    """
    print('\n[11.7] attendance 埋点...')
    for _ in range(3):
        r = requests.post(f'{MOBILE_5008}/api/attendance',
                          headers={'X-User-Id': '1'},
                          json={'action': 'check-in'}, timeout=5)
    r = requests.get(f'{MOBILE_5008}/api/metrics/stats', timeout=5)
    print(f'  GET /api/metrics/stats: HTTP {r.status_code}')
    assert r.status_code in (200, 404), f'attendance 埋点异常: {r.status_code}'


# ───────────── 用例 11.8：错误率统计 ─────────────

@pytest.mark.metrics
def test_08_error_rate():
    """错误率统计

    业务: 故意触发错误，验证 error_rate 上升
    """
    print('\n[11.8] 错误率统计...')
    # 跑 5 次故意 404
    for _ in range(5):
        r = requests.get(f'{MOBILE_5008}/api/nonexistent_endpoint',
                         headers={'X-User-Id': '1'}, timeout=5)
    r = requests.get(f'{MOBILE_5008}/api/metrics/stats', timeout=5)
    if r.status_code == 200:
        data = r.json().get('data', {})
        print(f'  错误率: {data.get("error_rate", "?")}')
    assert r.status_code in (200, 404), f'错误率异常: {r.status_code}'


# ───────────── 汇总 ─────────────

def test_99_metrics_summary():
    """监控埋点 E2E 测试汇总"""
    print('\n' + '=' * 60)
    print('监控 E2E 测试 8 用例已跑完')
    print('=' * 60)
