# -*- coding: utf-8 -*-
"""
[v3.7.2] Prometheus metrics 基础接入

为 dispatch_center 提供 metrics：
- 请求总数（按端点 + method + status）
- 请求延迟（histogram）
- DLQ 重试统计
- 业务事件计数

使用:
    from mobile_api_ai.dispatch_center._metrics import (
        metrics,
        REQUEST_COUNT,
        REQUEST_LATENCY,
        DLQ_RETRIES,
        DLQ_POISONED,
        record_request,
        record_dlq_retry,
    )

    @metrics
    @app.route('/api/xxx')
    def my_endpoint():
        ...

依赖: pip install prometheus_client
"""
import os
import time
import logging
from typing import Optional, Callable
from functools import wraps

logger = logging.getLogger(__name__)

# 尝试导入 prometheus_client（可选依赖）
try:
    from prometheus_client import (
        Counter, Histogram, Gauge, Summary,
        generate_latest, CONTENT_TYPE_LATEST,
        REGISTRY,
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning(
        '[v3.7.2 metrics] prometheus_client 未安装，metrics 不可用。'
        '运行: pip install prometheus_client'
    )


# ==================== Metrics 定义 ====================

if PROMETHEUS_AVAILABLE:
    # 请求总数
    REQUEST_COUNT = Counter(
        'dispatch_center_request_total',
        'Total dispatch_center requests',
        ['endpoint', 'method', 'status']
    )

    # 请求延迟（秒）
    REQUEST_LATENCY = Histogram(
        'dispatch_center_request_latency_seconds',
        'Request latency in seconds',
        ['endpoint', 'method'],
        buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
    )

    # DLQ 重试
    DLQ_RETRIES = Counter(
        'dispatch_center_dlq_retries_total',
        'DLQ retry attempts',
        ['result']  # success/failed/poisoned
    )

    # 当前 DLQ 队列长度
    DLQ_QUEUE_SIZE = Gauge(
        'dispatch_center_dlq_queue_size',
        'Current DLQ queue size (pending retries)'
    )

    # 业务事件
    BUSINESS_EVENTS = Counter(
        'dispatch_center_business_events_total',
        'Business events',
        ['event_type']  # order_created, task_assigned, etc.
    )

    # 数据库连接池
    DB_POOL_SIZE = Gauge(
        'dispatch_center_db_pool_size',
        'Current DB pool size',
        ['state']  # active/idle/total
    )

    # 缓存命中率
    CACHE_HITS = Counter(
        'dispatch_center_cache_total',
        'Cache hits/misses',
        ['cache_name', 'result']  # hit/miss
    )


# ==================== 装饰器与辅助函数 ====================

def record_request(endpoint: str, method: str, status: int, latency_seconds: float):
    """记录请求"""
    if not PROMETHEUS_AVAILABLE:
        return

    REQUEST_COUNT.labels(
        endpoint=endpoint,
        method=method,
        status=str(status),
    ).inc()

    REQUEST_LATENCY.labels(
        endpoint=endpoint,
        method=method,
    ).observe(latency_seconds)


def record_dlq_retry(result: str, count: int = 1):
    """记录 DLQ 重试结果"""
    if not PROMETHEUS_AVAILABLE:
        return

    DLQ_RETRIES.labels(result=result).inc(count)


def record_business_event(event_type: str, count: int = 1):
    """记录业务事件"""
    if not PROMETHEUS_AVAILABLE:
        return

    BUSINESS_EVENTS.labels(event_type=event_type).inc(count)


def record_cache(cache_name: str, hit: bool):
    """记录缓存命中"""
    if not PROMETHEUS_AVAILABLE:
        return

    CACHE_HITS.labels(
        cache_name=cache_name,
        result='hit' if hit else 'miss',
    ).inc()


def metrics_decorator(app):
    """Flask app 装饰器：自动记录所有 endpoint 的 metrics

    用法:
        from mobile_api_ai.dispatch_center._metrics import metrics_decorator
        app = create_app()
        metrics_decorator(app)
    """
    if not PROMETHEUS_AVAILABLE:
        logger.warning('[v3.7.2 metrics] prometheus_client 不可用，metrics_decorator 不生效')
        return

    @app.before_request
    def _before_request():
        from flask import request, g
        g._metrics_start_time = time.time()

    @app.after_request
    def _after_request(response):
        from flask import request, g
        start = getattr(g, '_metrics_start_time', None)
        if start is not None:
            latency = time.time() - start
            record_request(
                endpoint=request.path,
                method=request.method,
                status=response.status_code,
                latency_seconds=latency,
            )
        return response


def metrics_endpoint(app):
    """添加 /metrics 端点（Prometheus 抓取）

    用法:
        from mobile_api_ai.dispatch_center._metrics import metrics_endpoint
        metrics_endpoint(app)

    Prometheus 配置:
        scrape_configs:
          - job_name: 'dispatch_center'
            metrics_path: '/metrics'
            static_configs:
              - targets: ['localhost:5003']
    """
    if not PROMETHEUS_AVAILABLE:
        logger.warning('[v3.7.2 metrics] prometheus_client 不可用，metrics 端点不可用')
        return

    @app.route('/metrics')
    def _metrics():
        return generate_latest(REGISTRY), 200, {'Content-Type': CONTENT_TYPE_LATEST}


# ==================== 集成 DLQ worker ====================

def integrate_dlq_metrics(_dlq_retry_module):
    """为 DLQ retry worker 集成 metrics

    用法:
        from mobile_api_ai.dispatch_center import _dlq_retry
        from mobile_api_ai.dispatch_center._metrics import integrate_dlq_metrics
        integrate_dlq_metrics(_dlq_retry)
    """
    if not PROMETHEUS_AVAILABLE:
        return

    original_dlq_retry_once = _dlq_retry_module._dlq_retry_once

    def wrapped_dlq_retry_once():
        """带 metrics 的重试入口"""
        records = _dlq_retry_module._fetch_pending_dlq_records(limit=_dlq_retry_module._DLQ_BATCH_SIZE)

        # 更新队列长度
        DLQ_QUEUE_SIZE.set(len(records) if records else 0)

        # 调用原始函数
        return original_dlq_retry_once()

    # 替换函数
    _dlq_retry_module._dlq_retry_once = wrapped_dlq_retry_once


# ==================== 健康检查 /metrics 兼容 ====================

def get_metrics_summary() -> dict:
    """获取 metrics 摘要（用于健康检查端点）

    即使没有 prometheus_client 也能工作
    """
    if not PROMETHEUS_AVAILABLE:
        return {
            'prometheus_available': False,
            'message': 'prometheus_client 未安装',
        }

    # 收集所有 metrics
    summary = {'prometheus_available': True}

    try:
        from prometheus_client import REGISTRY
        for metric in REGISTRY.collect():
            summary[metric.name] = {
                'type': metric.type,
                'help': metric.documentation,
            }
    except Exception as e:
        summary['error'] = str(e)

    return summary


__all__ = [
    'PROMETHEUS_AVAILABLE',
    'REQUEST_COUNT', 'REQUEST_LATENCY',
    'DLQ_RETRIES', 'DLQ_QUEUE_SIZE',
    'BUSINESS_EVENTS', 'DB_POOL_SIZE', 'CACHE_HITS',
    'record_request', 'record_dlq_retry', 'record_business_event', 'record_cache',
    'metrics_decorator', 'metrics_endpoint', 'integrate_dlq_metrics',
    'get_metrics_summary',
]
