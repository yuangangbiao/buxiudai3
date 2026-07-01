#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
容错边界控制模块 - 确保系统稳定性

警告：本模块是 modules/circuit_breaker.py 的重复实现。
新代码应优先使用 modules/circuit_breaker.py 中的 CircuitBreaker 类。
此模块保留用于向后兼容，将在未来版本中移除。
"""

import os
import time
import logging
import random
from typing import Optional, Callable, Any
from enum import Enum
from dataclasses import dataclass, field
from threading import Lock
from collections import deque

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True

    def get_delay(self, attempt: int) -> float:
        """
        计算重试延迟

        Args:
            attempt: 当前重试次数（从0开始）

        Returns:
            float: 延迟秒数
        """
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
        """记录成功请求"""
        self.total_requests += 1
        self.successful_requests += 1
        self.recent_successes.append({'time': time.time(), 'latency': latency})

    def record_failure(self, error_type: str = "unknown"):
        """记录失败请求"""
        self.total_requests += 1
        self.failed_requests += 1
        self.recent_failures.append({'time': time.time(), 'error': error_type})

    def record_retry(self):
        """记录重试"""
        self.retried_requests += 1

    def record_circuit_breaker_triggered(self):
        """记录熔断器触发"""
        self.circuit_breaker_triggered += 1

    def get_failure_rate(self) -> float:
        """获取失败率"""
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests

    def get_success_rate(self) -> float:
        """获取成功率"""
        return 1.0 - self.get_failure_rate()

    def to_dict(self) -> dict:
        """转换为字典"""
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
    """容错边界控制器"""

    def __init__(self):
        """初始化容错控制器"""
        self.config = {
            'max_failure_rate': float(os.environ.get('CB_FAILURE_RATE_THRESHOLD', '0.5')),
            'circuit_breaker_threshold': int(float(os.environ.get('CB_FAILURE_THRESHOLD', '50'))),
            'circuit_breaker_timeout': int(float(os.environ.get('CB_OPEN_TIMEOUT', '30'))),
            'half_open_max_requests': int(float(os.environ.get('CB_HALF_OPEN_REQUESTS', '3'))),
            'failure_rate_window': 100
        }
        self.metrics = FaultToleranceMetrics()
        self.circuit_state = CircuitState.CLOSED
        self.last_failure_time: float = 0
        self.consecutive_failures: int = 0
        self.consecutive_successes: int = 0
        self._half_open_requests: int = 0
        self._lock = Lock()
        self.retry_config = RetryConfig()

    def should_retry(self, attempt: int) -> bool:
        """
        判断是否应该重试

        Args:
            attempt: 当前尝试次数（从0开始）

        Returns:
            bool: 是否应该重试
        """
        return attempt < self.retry_config.max_retries

    def get_retry_delay(self, attempt: int) -> float:
        """
        获取重试延迟

        Args:
            attempt: 当前尝试次数

        Returns:
            float: 延迟秒数
        """
        return self.retry_config.get_delay(attempt)

    def should_allow_request(self) -> bool:
        """
        判断是否允许请求（熔断器检查）

        Returns:
            bool: 是否允许请求
        """
        with self._lock:
            if self.circuit_state == CircuitState.CLOSED:
                return True

            if self.circuit_state == CircuitState.OPEN:
                if time.time() - self.last_failure_time >= self.config['circuit_breaker_timeout']:
                    self._transition_to_half_open()
                    return True
                return False

            if self.circuit_state == CircuitState.HALF_OPEN:
                if self._half_open_requests < self.config['half_open_max_requests']:
                    self._half_open_requests += 1
                    return True
                return False

            return True

    def record_success(self):
        """记录成功操作"""
        with self._lock:
            self.metrics.record_success()
            self.consecutive_failures = 0

            if self.circuit_state == CircuitState.HALF_OPEN:
                self.consecutive_successes += 1
                if self.consecutive_successes >= self.config['half_open_max_requests']:
                    self._transition_to_closed()

    def record_failure(self, error_type: str = "unknown"):
        """
        记录失败操作

        Args:
            error_type: 错误类型
        """
        with self._lock:
            self.metrics.record_failure(error_type)
            self.last_failure_time = time.time()
            self.consecutive_failures += 1
            self.consecutive_successes = 0

            if self.circuit_state == CircuitState.HALF_OPEN:
                self._transition_to_open()
                self.metrics.record_circuit_breaker_triggered()
                return

            failure_rate = self.metrics.get_failure_rate()
            if (failure_rate > self.config['max_failure_rate'] or
                    self.consecutive_failures >= self.config['circuit_breaker_threshold']):
                self._transition_to_open()
                self.metrics.record_circuit_breaker_triggered()
                logger.warning(
                    f"熔断器开启: 失败率={failure_rate:.2%}, "
                    f"连续失败={self.consecutive_failures}"
                )

    def _transition_to_open(self):
        """转换到OPEN状态"""
        if self.circuit_state != CircuitState.OPEN:
            logger.info("熔断器状态: CLOSED/HALF_OPEN -> OPEN")
            self.circuit_state = CircuitState.OPEN
            self._half_open_requests = 0

    def _transition_to_half_open(self):
        """转换到HALF_OPEN状态"""
        logger.info("熔断器状态: OPEN -> HALF_OPEN")
        self.circuit_state = CircuitState.HALF_OPEN
        self._half_open_requests = 0
        self.consecutive_successes = 0

    def _transition_to_closed(self):
        """转换到CLOSED状态"""
        logger.info("熔断器状态: HALF_OPEN -> CLOSED")
        self.circuit_state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.consecutive_successes = 0

    def get_state(self) -> str:
        """获取当前熔断器状态"""
        return self.circuit_state.value

    def reset(self):
        """重置熔断器"""
        with self._lock:
            self._transition_to_closed()
            self.metrics = FaultToleranceMetrics()
            logger.info("熔断器已重置")

    def execute_with_retry(
        self,
        func: Callable,
        *args,
        fallback: Optional[Callable] = None,
        **kwargs
    ) -> Any:
        """
        执行带重试的函数

        Args:
            func: 要执行的函数
            *args: 函数位置参数
            fallback: 降级函数（可选）
            **kwargs: 函数关键字参数

        Returns:
            Any: 函数执行结果

        Raises:
            Exception: 所有重试都失败后抛出异常
        """
        last_exception = None

        for attempt in range(self.retry_config.max_retries + 1):
            if not self.should_allow_request():
                if fallback:
                    logger.warning("熔断器开启，执行降级函数")
                    return fallback(*args, **kwargs)
                raise Exception("服务不可用（熔断器开启）")

            try:
                result = func(*args, **kwargs)
                if attempt > 0:
                    self.metrics.record_retry()
                self.record_success()
                return result

            except Exception as e:
                last_exception = e
                logger.warning(f"执行失败 (尝试 {attempt + 1}): {e}")
                self.record_failure(type(e).__name__)

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
