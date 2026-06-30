# -*- coding: utf-8 -*-
"""core/metrics.py 的集成测试(真业务,无 mock)。

测试覆盖:
- MetricsCollector 全部方法(increment/record_latency/get_counters/get_p99/get_summary)
- 线程安全(不 mock threading.Lock,真并发验证)
- 模块级单例函数(record_metric/record_latency/get_metrics)
"""
import threading

import pytest

from core import metrics as metrics_module
from core.metrics import MetricsCollector, record_metric, record_latency, get_metrics


@pytest.fixture
def collector():
    """每个 test 用全新 MetricsCollector 实例,避免模块单例污染。"""
    return MetricsCollector()


def test_increment_default_value(collector):
    """increment(name) 默认 value=1,首次调用后计数器为 1。"""
    collector.increment("api_calls")
    assert collector.get_counters() == {"api_calls": 1}


def test_increment_custom_value(collector):
    """increment(name, value=N) 应累加 N(可大于 1)。"""
    collector.increment("bytes_sent", value=1024)
    collector.increment("bytes_sent", value=512)
    assert collector.get_counters() == {"bytes_sent": 1536}


def test_get_counters_returns_copy_not_reference(collector):
    """get_counters 必须返副本——修改返回值不能污染内部 _counters。"""
    collector.increment("x", value=1)
    snapshot = collector.get_counters()
    snapshot["x"] = 999
    snapshot["new"] = "leak"
    assert collector.get_counters() == {"x": 1}


def test_record_latency_creates_list_on_first_call(collector):
    """首次 record_latency 必须创建 list 而非覆盖。"""
    collector.record_latency("db_query", 12.5)
    collector.record_latency("db_query", 8.0)
    assert collector._histograms["db_query"] == [12.5, 8.0]


def test_get_p99_returns_zero_for_unrecorded_metric(collector):
    """未记录过的指标返 0(不能抛 KeyError)。"""
    assert collector.get_p99("never_recorded") == 0


def test_get_p99_picks_99th_percentile(collector):
    """p99 必须按 math.ceil(N*0.99) 取索引的值。"""
    for i in range(1, 101):
        collector.record_latency("rt", float(i))
    p99 = collector.get_p99("rt")
    sorted_vals = sorted(collector._histograms["rt"])
    import math
    expected_idx = max(0, int(math.ceil(len(sorted_vals) * 0.99)) - 1)
    assert p99 == sorted_vals[expected_idx]


def test_get_summary_combines_counters_and_p99(collector):
    """get_summary 必须同时输出 counters(快照)和 p99(每指标)。"""
    collector.increment("req_total", value=3)
    collector.record_latency("req_lat", 5.0)
    collector.record_latency("req_lat", 15.0)
    summary = collector.get_summary()
    assert summary["counters"] == {"req_total": 3}
    assert "req_lat" in summary["p99"]
    assert summary["p99"]["req_lat"] > 0


def test_module_level_record_metric_uses_global_singleton():
    """record_metric(name, value) 必须走 _metrics 全局单例。"""
    metrics_module._metrics = MetricsCollector()
    record_metric("module_test", value=7)
    record_metric("module_test", value=3)
    assert get_metrics()["counters"]["module_test"] == 10


def test_module_level_record_latency_uses_global_singleton():
    """record_latency(name, ms) 必须走 _metrics 全局单例。"""
    metrics_module._metrics = MetricsCollector()
    record_latency("mod_lat", 1.0)
    record_latency("mod_lat", 9.0)
    assert "mod_lat" in get_metrics()["p99"]


def test_concurrent_increment_thread_safety(collector):
    """1000 次并发 increment 必须全部计入(Lock 保护)。"""
    def _worker():
        for _ in range(100):
            collector.increment("concurrent")

    threads = [threading.Thread(target=_worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert collector.get_counters()["concurrent"] == 1000
