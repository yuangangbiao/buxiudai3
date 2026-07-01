#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
容错边界控制模块 - 确保系统稳定性（兼容层）

内部熔断逻辑委托给 modules/circuit_breaker.py 的 CircuitBreaker。
保留 RetryConfig、FaultToleranceMetrics、execute_with_retry 接口不变。
"""

import os
import time
import logging
import random
from typing import Optional, Callable, Any

from dataclasses import dataclass, field
from threading import Lock
from collections import deque

from modules.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    get_circuit_breaker,
)

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True

    def get_delay(self, attempt: int) -> float:
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        if self.jitter:
            delay = delay * (0.5 + random.random())
        return delay


@dataclass
class FaultToleranceMetrics:
    """容错指标"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    retried_requests: int = 0
    circuit_breaker_triggered: int = 0
    recent_failures: deque = field(default_factory=lambda: deque(maxlen=int(os.getenv('FT_RECENT_MAXLEN', '100'))))
    recent_successes: deque = field(default_factory=lambda: deque(maxlen=int(os.getenv('FT_RECENT_MAXLEN', '100'))))

    def record_success(self, latency: float = 0):
        self.total_requests += 1
        self.successful_requests += 1
        self.recent_successes.append({'time': time.time(), 'latency': latency})

    def record_failure(self, error_type: str = "unknown"):
        self.total_requests += 1
        self.failed_requests += 1
        self.recent_failures.append({'time': time.time(), 'error': error_type})

    def record_retry(self):
        self.retried_requests += 1

    def record_circuit_breaker_triggered(self):
        self.circuit_breaker_triggered += 1

    def get_failure_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests

    def get_success_rate(self) -> float:
        return 1.0 - self.get_failure_rate()

    def to_dict(self) -> dict:
        return {
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'retried_requests': self.retried_requests,
            'circuit_breaker_triggered': self.circuit_breaker_triggered,
            'failure_rate': round(self.get_failure_rate() * 100, 2),
            'success_rate': round(self.get_success_rate() * 100, 2)
        }


class FaultTolerance:
    """容错边界控制器（兼容层，熔断逻辑委托给 CircuitBreaker）"""

    def __init__(self):
        self._cb: CircuitBreaker = get_circuit_breaker(
            'fault_tolerance',
            failure_threshold=int(float(os.environ.get('CB_FAILURE_THRESHOLD', '50'))),
            failure_rate_threshold=float(os.environ.get('CB_FAILURE_RATE_THRESHOLD', '0.5')),
            half_open_max_requests=int(float(os.environ.get('CB_HALF_OPEN_REQUESTS', '3'))),
            open_timeout=float(os.environ.get('CB_OPEN_TIMEOUT', '30')),
        )
        self.metrics = FaultToleranceMetrics()
        self._lock = Lock()
        self.retry_config = RetryConfig()

    def should_retry(self, attempt: int) -> bool:
        return attempt < self.retry_config.max_retries

    def get_retry_delay(self, attempt: int) -> float:
        return self.retry_config.get_delay(attempt)

    def should_allow_request(self) -> bool:
        return self._cb.allow_request()

    def record_success(self):
        self._cb.record_success()
        self.metrics.record_success()

    def record_failure(self, error_type: str = "unknown"):
        self._cb.record_failure()
        self.metrics.record_failure(error_type)
        if self._cb.state in (CircuitState.OPEN,):
            self.metrics.record_circuit_breaker_triggered()

    def get_state(self) -> str:
        return self._cb.state.value

    def reset(self):
        with self._lock:
            self.metrics = FaultToleranceMetrics()
            logger.info("熔断器已重置（新建 metrics）")

    def execute_with_retry(
        self,
        func: Callable,
        *args,
        fallback: Optional[Callable] = None,
        **kwargs
    ) -> Any:
        last_exception = None

        for attempt in range(self.retry_config.max_retries + 1):
            if not self._cb.allow_request():
                if fallback:
                    logger.warning("熔断器开启，执行降级函数")
                    return fallback(*args, **kwargs)
                raise Exception("服务不可用（熔断器开启）")

            try:
                result = func(*args, **kwargs)
                if attempt > 0:
                    self.metrics.record_retry()
                self._cb.record_success()
                self.metrics.record_success()
                return result

            except Exception as e:
                last_exception = e
                logger.warning(f"执行失败 (尝试 {attempt + 1}): {e}")
                self._cb.record_failure()
                self.metrics.record_failure(type(e).__name__)

                if self._cb.state == CircuitState.OPEN:
                    self.metrics.record_circuit_breaker_triggered()

                if self.should_retry(attempt):
                    delay = self.get_retry_delay(attempt)
                    logger.info(f"等待 {delay:.1f}秒后重试...")
                    time.sleep(delay)
                else:
                    break

        if fallback:
            logger.warning("所有重试失败，执行降级函数")
            try:
                return fallback(*args, **kwargs)
            except Exception as fallback_error:
                logger.error(f"降级函数也失败: {fallback_error}")

        raise last_exception


fault_tolerance = FaultTolerance()
