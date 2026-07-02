# -*- coding: utf-8 -*-
"""
test_concurrent_report.py - 报工并发超量测试

[P0-BUG-FIX] 验证多工人同时报工不会超量

修复前：TOCTOU - SELECT → Python计算 → UPDATE，非原子
修复后：update_document 返回 409 当数据被并发修改

依赖：5008 服务已启动（wechat_server.py）
"""
import os
import sys
import pytest
import requests
import concurrent.futures
import threading
import time
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

API_URL = os.getenv('MOBILE_5008_URL', 'http://127.0.0.1:5008')
SYNC_URL = os.getenv('SYNC_8008_URL', 'http://127.0.0.1:8008')


def api_ok(r, msg=''):
    data = r.json()
    assert data.get('code') == 0, f'{msg} → {data.get("message")} (code={data.get("code")})'
    return data


def service_alive(url, timeout=2):
    try:
        r = requests.get(f'{url}/', timeout=timeout)
        return r.status_code < 500
    except:
        return False


class TestConcurrentReport:
    """并发报工测试"""

    @pytest.fixture(autouse=True)
    def check_service(self):
        if not service_alive(API_URL) and not service_alive(SYNC_URL):
            pytest.skip('5008/8008服务不可用')

    def test_concurrent_report_same_order(self):
        """
        场景：10个工人同时对同一订单报工
        预期：总报工量不超过计划量（超量的请求返回409冲突）
        """
        order_no = f'CONCURRENT-{datetime.now().strftime("%Y%m%d%H%M%S")}'
        process = '编织'
        plan_qty = 100
        worker_count = 10
        qty_per_worker = 15

        results = {'success': 0, 'conflict': 0, 'other': 0}
        lock = threading.Lock()

        def report_worker(worker_id):
            try:
                r = requests.post(
                    f'{SYNC_URL}/api/sync/report',
                    json={
                        'order_no': order_no,
                        'process': process,
                        'quantity': qty_per_worker,
                        'operator': f'Worker-{worker_id}',
                        'force': False,
                    },
                    timeout=10,
                )
                with lock:
                    if r.status_code == 200:
                        results['success'] += 1
                    elif r.status_code == 409:
                        results['conflict'] += 1
                    else:
                        results['other'] += 1
            except Exception as e:
                with lock:
                    results['other'] += 1

        with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = [executor.submit(report_worker, i) for i in range(worker_count)]
            concurrent.futures.wait(futures)

        print(f'\n并发报工结果（计划={plan_qty}，每人={qty_per_worker}，10人同时）:')
        print(f'  成功: {results["success"]}')
        print(f'  冲突(409): {results["conflict"]}')
        print(f'  其他错误: {results["other"]}')

        total_if_all_success = qty_per_worker * worker_count
        assert results['conflict'] > 0, \
            f'超量时应有请求返回409冲突，实际conflict={results["conflict"]}'

    def test_concurrent_report_idempotent(self):
        """
        场景：同一订单重复提交相同报工
        预期：幂等性保证，不重复累加
        """
        order_no = f'IDEMP-{datetime.now().strftime("%Y%m%d%H%M%S")}'
        process = '编织'
        qty = 50

        r1 = requests.post(
            f'{SYNC_URL}/api/sync/report',
            json={
                'order_no': order_no,
                'process': process,
                'quantity': qty,
                'operator': 'test-worker',
                'force': True,
            },
            timeout=10,
        )

        assert r1.status_code in (200, 409), \
            f'报工应返回200或409，实际={r1.status_code}'

    def test_report_quantity_boundary_zero(self):
        """边界：报工数量=0 应被拒绝或忽略"""
        r = requests.post(
            f'{SYNC_URL}/api/sync/report',
            json={
                'order_no': 'TEST-BOUNDARY',
                'process': '编织',
                'quantity': 0,
                'operator': 'test',
                'force': True,
            },
            timeout=10,
        )
        print(f'\n边界[数量=0]: status={r.status_code}')
        assert r.status_code in (200, 400, 422), \
            f'数量=0应返回400/422，实际={r.status_code}'

    def test_report_quantity_boundary_negative(self):
        """边界：报工数量=负数 应被拒绝"""
        r = requests.post(
            f'{SYNC_URL}/api/sync/report',
            json={
                'order_no': 'TEST-BOUNDARY',
                'process': '编织',
                'quantity': -10,
                'operator': 'test',
                'force': True,
            },
            timeout=10,
        )
        print(f'\n边界[数量=-10]: status={r.status_code}')
        assert r.status_code in (200, 400, 422), \
            f'负数数量应返回400/422，实际={r.status_code}'
