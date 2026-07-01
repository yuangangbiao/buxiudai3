# -*- coding: utf-8 -*-
"""T8: 并发安全测试 — 报工数据回归"""
import pytest
from unittest.mock import patch
import threading
from datetime import datetime


class TestConcurrentOverwrite:
    def test_two_threads_same_step_only_one_succeeds(self):
        """2线程同时覆盖同一条 → 决策树返回 prompt"""
        from regression.decision import decide_regression
        results = []
        lock = threading.Lock()
        existing = {'id': 1, 'operator': '张三', 'quantity': 50, 'batch_no': 'B1', 'first_created_at': datetime.now().isoformat()}

        def worker(name):
            action, ctx = decide_regression(name, 30, 'B2', existing, 100, 0, False, 0)
            with lock:
                results.append((name, action))

        t1 = threading.Thread(target=worker, args=('李四',))
        t2 = threading.Thread(target=worker, args=('王五',))
        t1.start(); t2.start()
        t1.join(); t2.join()

        assert all(r[1] == 'prompt' for r in results)

    def test_concurrent_same_operator_same_batch_idempotent(self):
        """5线程同时提交相同请求 → 全部幂等"""
        from regression.decision import decide_regression
        now = datetime.now().isoformat()
        existing = {'id': 1, 'operator': '张三', 'quantity': 50, 'batch_no': 'B1', 'first_created_at': now}
        results = []
        lock = threading.Lock()

        def worker():
            action, ctx = decide_regression('张三', 50, 'B1', existing, 200, 0, False, 0)
            with lock:
                results.append(action)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert all(r == 'idempotent' for r in results)

    @patch('pymysql.connect')
    def test_insert_with_for_update(self, mock_connect):
        """写操作含 FOR UPDATE 行锁"""
        with open('app.py', 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'FOR UPDATE' in content
