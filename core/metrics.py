"""Prometheus 指标采集"""
import time
import logging

logger = logging.getLogger(__name__)

class MetricsCollector:
    def __init__(self):
        self._counters = {}
        self._histograms = {}
        self._lock = __import__('threading').Lock()

    def increment(self, name, value=1):
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + value

    def record_latency(self, name, ms):
        with self._lock:
            if name not in self._histograms:
                self._histograms[name] = []
            self._histograms[name].append(ms)

    def get_counters(self):
        return dict(self._counters)

    def get_p99(self, name):
        values = self._histograms.get(name, [])
        if not values:
            return 0
        values.sort()
        import math
        return values[max(0, int(math.ceil(len(values) * 0.99)) - 1)]

    def get_summary(self):
        return {
            'counters': self.get_counters(),
            'p99': {k: self.get_p99(k) for k in self._histograms}
        }

# 全局单例
_metrics = MetricsCollector()

def record_metric(name, value=1):
    _metrics.increment(name, value)

def record_latency(name, ms):
    _metrics.record_latency(name, ms)

def get_metrics():
    return _metrics.get_summary()
