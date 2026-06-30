# -*- coding: utf-8 -*-
"""
[v3.7.5] Prometheus metrics 单元测试

[注意] 使用 importlib 直接加载 _metrics，绕过 dispatch_center.__init__.py
"""
import os
import sys
import importlib.util
import pytest
from unittest.mock import MagicMock, patch


_metrics_module_cache = None


def _load_metrics_directly():
    """直接加载 _metrics.py，绕过 __init__.py（使用缓存避免重复注册）"""
    global _metrics_module_cache
    if _metrics_module_cache is not None:
        return _metrics_module_cache

    metrics_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        'mobile_api_ai', 'dispatch_center', '_metrics.py'
    )
    spec = importlib.util.spec_from_file_location("_metrics_module_unique", metrics_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _metrics_module_cache = module
    return module


@pytest.fixture(scope='session')
def metrics_module():
    """加载 metrics 模块（session scope 确保单例）"""
    return _load_metrics_directly()


class TestMetricsFallback:
    """metrics 在无 prometheus_client 时优雅降级"""

    def test_prometheus_available_flag(self, metrics_module):
        """PROMETHEUS_AVAILABLE 标志"""
        assert isinstance(metrics_module.PROMETHEUS_AVAILABLE, bool)

    def test_record_request_no_crash(self, metrics_module):
        """record_request 不抛异常"""
        metrics_module.record_request('/api/test', 'GET', 200, 0.1)

    def test_record_dlq_retry_no_crash(self, metrics_module):
        """record_dlq_retry 不抛异常"""
        metrics_module.record_dlq_retry('success')
        metrics_module.record_dlq_retry('failed', count=5)

    def test_record_business_event_no_crash(self, metrics_module):
        """record_business_event 不抛异常"""
        metrics_module.record_business_event('order_created')
        metrics_module.record_business_event('task_assigned', count=10)

    def test_record_cache_no_crash(self, metrics_module):
        """record_cache 不抛异常"""
        metrics_module.record_cache('operators', hit=True)
        metrics_module.record_cache('operators', hit=False)


class TestMetricsSummary:
    """metrics 摘要"""

    def test_get_metrics_summary(self, metrics_module):
        """获取 metrics 摘要"""
        summary = metrics_module.get_metrics_summary()
        assert 'prometheus_available' in summary
        assert isinstance(summary['prometheus_available'], bool)


@pytest.mark.skipif(
    not _load_metrics_directly().PROMETHEUS_AVAILABLE,
    reason='prometheus_client 未安装'
)
class TestMetricsIntegration:
    """metrics 集成测试（需要 prometheus_client）"""

    def test_request_count_increments(self, metrics_module):
        """请求计数自增"""
        for _ in range(5):
            metrics_module.record_request('/api/test', 'GET', 200, 0.1)
        count = metrics_module.REQUEST_COUNT.labels(
            endpoint='/api/test',
            method='GET',
            status='200',
        )._value.get()
        assert count >= 5

    def test_dlq_retries_by_result(self, metrics_module):
        """DLQ 重试按结果分类"""
        metrics_module.record_dlq_retry('success', count=3)
        metrics_module.record_dlq_retry('failed', count=2)
        metrics_module.record_dlq_retry('poisoned')

        success = metrics_module.DLQ_RETRIES.labels(result='success')._value.get()
        failed = metrics_module.DLQ_RETRIES.labels(result='failed')._value.get()
        poisoned = metrics_module.DLQ_RETRIES.labels(result='poisoned')._value.get()

        assert success >= 3
        assert failed >= 2
        assert poisoned >= 1

    def test_business_events(self, metrics_module):
        """业务事件计数"""
        metrics_module.record_business_event('order_created', count=10)
        metrics_module.record_business_event('task_assigned', count=20)

        orders = metrics_module.BUSINESS_EVENTS.labels(event_type='order_created')._value.get()
        tasks = metrics_module.BUSINESS_EVENTS.labels(event_type='task_assigned')._value.get()

        assert orders >= 10
        assert tasks >= 20

    def test_dlq_queue_size_gauge(self, metrics_module):
        """DLQ 队列长度 Gauge"""
        metrics_module.DLQ_QUEUE_SIZE.set(42)
        assert metrics_module.DLQ_QUEUE_SIZE._value.get() == 42
