# -*- coding: utf-8 -*-
"""
监控指标模块 - 业务指标埋点

提供关键业务指标监控：
- 报工成功率
- API响应时间
- 错误率
- 队列深度

使用方式：
    from metrics import metrics

    # 记录API调用
    metrics.api_request('/api/process/report', 0.05, 200)

    # 记录报工
    metrics.report_submitted(order_id=123, worker_id='OP001', success=True)

    # 获取指标
    print(metrics.get_stats())
"""
import time
import threading
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, Any, Optional


class MetricsCollector:
    """指标收集器 - 线程安全"""

    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self._lock = threading.Lock()

        self._api_requests = deque(maxlen=max_history)
        self._reports = deque(maxlen=max_history)
        self._errors = deque(maxlen=max_history)
        self._queue_depth = 0

        self._counters = defaultdict(int)
        self._histograms = defaultdict(list)

    def record_api_request(self, endpoint: str, duration: float, status_code: int):
        """记录API请求"""
        with self._lock:
            self._api_requests.append({
                'timestamp': datetime.now(),
                'endpoint': endpoint,
                'duration': duration,
                'status_code': status_code
            })
            self._counters['api_requests_total'] += 1
            self._histograms[f'api_duration_{endpoint}'].append(duration)
            if status_code >= 400:
                self._counters['api_errors_total'] += 1

    def record_report(self, order_id: int, worker_id: str, success: bool):
        """记录报工"""
        with self._lock:
            self._reports.append({
                'timestamp': datetime.now(),
                'order_id': order_id,
                'worker_id': worker_id,
                'success': success
            })
            self._counters['reports_total'] += 1
            if success:
                self._counters['reports_success'] += 1
            else:
                self._counters['reports_failed'] += 1

    def record_error(self, error_type: str, message: str, endpoint: str = None):
        """记录错误"""
        with self._lock:
            self._errors.append({
                'timestamp': datetime.now(),
                'error_type': error_type,
                'message': message,
                'endpoint': endpoint
            })
            self._counters['errors_total'] += 1
            self._counters[f'errors_{error_type}'] += 1

    def set_queue_depth(self, depth: int):
        """设置队列深度"""
        with self._lock:
            self._queue_depth = depth

    def get_stats(self, minutes: int = 60) -> Dict[str, Any]:
        """获取统计信息（最近N分钟）"""
        with self._lock:
            now = datetime.now()
            cutoff = now - timedelta(minutes=minutes)

            recent_requests = [r for r in self._api_requests if r['timestamp'] >= cutoff]
            recent_reports = [r for r in self._reports if r['timestamp'] >= cutoff]
            recent_errors = [e for e in self._errors if e['timestamp'] >= cutoff]

            request_durations = [r['duration'] for r in recent_requests]
            avg_duration = sum(request_durations) / len(request_durations) if request_durations else 0

            success_count = sum(1 for r in recent_reports if r['success'])
            total_reports = len(recent_reports)
            report_success_rate = (success_count / total_reports * 100) if total_reports > 0 else 0

            error_rate = (len(recent_errors) / len(recent_requests) * 100) if recent_requests else 0

            status_codes = defaultdict(int)
            for r in recent_requests:
                status_codes[r['status_code']] += 1

            endpoints = defaultdict(int)
            for r in recent_requests:
                endpoints[r['endpoint']] += 1

            return {
                'timestamp': now.isoformat(),
                'period_minutes': minutes,
                'api': {
                    'total_requests': len(recent_requests),
                    'avg_duration_ms': round(avg_duration * 1000, 2),
                    'error_rate': round(error_rate, 2),
                    'status_codes': dict(status_codes),
                    'top_endpoints': dict(sorted(endpoints.items(), key=lambda x: x[1], reverse=True)[:10])
                },
                'reports': {
                    'total': total_reports,
                    'success': success_count,
                    'failed': total_reports - success_count,
                    'success_rate': round(report_success_rate, 2)
                },
                'errors': {
                    'total': len(recent_errors),
                    'by_type': dict(self._counters),
                    'recent': recent_errors[-10:]
                },
                'queue': {
                    'depth': self._queue_depth
                },
                'counters': dict(self._counters)
            }

    def reset(self):
        """重置所有指标"""
        with self._lock:
            self._api_requests.clear()
            self._reports.clear()
            self._errors.clear()
            self._counters.clear()
            self._histograms.clear()
            self._queue_depth = 0


class Timer:
    """计时器上下文管理器"""

    def __init__(self, collector: MetricsCollector, endpoint: str):
        self.collector = collector
        self.endpoint = endpoint
        self.start_time = None
        self.status_code = 200

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        if exc_type is not None:
            self.status_code = 500
            self.collector.record_error(exc_type.__name__, str(exc_val), self.endpoint)
        self.collector.record_api_request(self.endpoint, duration, self.status_code)
        return False

    def set_status(self, code: int):
        """手动设置状态码"""
        self.status_code = code


metrics = MetricsCollector()


def track_request(endpoint: str):
    """装饰器：自动追踪API请求"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with Timer(metrics, endpoint):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def record_report(order_id: int, worker_id: str, success: bool):
    """记录报工"""
    metrics.record_report(order_id, worker_id, success)


def record_error(error_type: str, message: str, endpoint: str = None):
    """记录错误"""
    metrics.record_error(error_type, message, endpoint)


def set_queue_depth(depth: int):
    """设置队列深度"""
    metrics.set_queue_depth(depth)


def get_stats(minutes: int = 60) -> Dict[str, Any]:
    """获取统计信息"""
    return metrics.get_stats(minutes)


def reset_metrics():
    """重置指标"""
    metrics.reset()
