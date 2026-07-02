#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""熔断恢复机制模块 - 含半开状态、平滑恢复、统计监控"""

import os
import time
import asyncio
import logging
from enum import Enum
from typing import Callable, Any, Optional
from threading import Lock
from dataclasses import dataclass, field
from collections import deque

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"       # 正常状态
    OPEN = "open"           # 熔断开启
    HALF_OPEN = "half_open"  # 半开状态（测试恢复）


@dataclass
class CircuitMetrics:
    """熔断器指标"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    success_rate: float = 1.0
    failure_rate: float = 0.0
    avg_response_time: float = 0.0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    state_changed_at: float = field(default_factory=time.time)
    recent_response_times: deque = field(default_factory=lambda: deque(maxlen=int(os.getenv('CB_RESPONSE_TIME_MAXLEN', '100'))))


class CircuitBreaker:
    """
    熔断器（支持平滑恢复）

    状态转换:
    - CLOSED -> OPEN: 失败率超过阈值
    - OPEN -> HALF_OPEN: 熔断超时后
    - HALF_OPEN -> CLOSED: 连续成功次数达标
    - HALF_OPEN -> OPEN: 再次失败
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 50,
        success_threshold: int = 3,
        failure_rate_threshold: float = 0.5,
        half_open_max_requests: int = 3,
        open_timeout: float = 30.0,
        recovery_timeout: float = 60.0,
        min_requests: int = 10
    ):
        """
        初始化熔断器

        Args:
            name: 熔断器名称
            failure_threshold: 连续失败次数阈值（触发熔断）
            success_threshold: 连续成功次数阈值（恢复）
            failure_rate_threshold: 失败率阈值（触发熔断，默认50%）
            half_open_max_requests: 半开状态下允许的最大测试请求数
            open_timeout: 熔断超时时间（秒）
            recovery_timeout: 恢复超时时间（秒）
            min_requests: 最小请求数（用于计算失败率）
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.failure_rate_threshold = failure_rate_threshold
        self.half_open_max_requests = half_open_max_requests
        self.open_timeout = open_timeout
        self.recovery_timeout = recovery_timeout
        self.min_requests = min_requests

        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._half_open_requests = 0
        self._lock = Lock()
        self._metrics = CircuitMetrics()
        self._last_state_change = time.time()

        logger.info(
            f"CircuitBreaker '{name}' initialized: "
            f"failure_threshold={failure_threshold}, "
            f"failure_rate_threshold={failure_rate_threshold:.2%}, "
            f"open_timeout={open_timeout}s"
        )

    @property
    def state(self) -> CircuitState:
        """获取当前状态"""
        with self._lock:
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._transition_to_half_open()
            return self._state

    @property
    def metrics(self) -> CircuitMetrics:
        """获取熔断器指标"""
        with self._lock:
            return CircuitMetrics(
                total_calls=self._metrics.total_calls,
                successful_calls=self._metrics.successful_calls,
                failed_calls=self._metrics.failed_calls,
                rejected_calls=self._metrics.rejected_calls,
                success_rate=self._metrics.success_rate,
                failure_rate=self._metrics.failure_rate,
                avg_response_time=self._metrics.avg_response_time,
                last_failure_time=self._metrics.last_failure_time,
                last_success_time=self._metrics.last_success_time,
                state_changed_at=self._metrics.state_changed_at
            )

    def _should_attempt_reset(self) -> bool:
        """判断是否应该尝试恢复"""
        elapsed = time.time() - self._last_state_change
        return elapsed >= self.open_timeout

    def _transition_to_half_open(self):
        """转换到半开状态"""
        logger.info(f"CircuitBreaker '{self.name}' transitioning to HALF_OPEN")
        self._state = CircuitState.HALF_OPEN
        self._half_open_requests = 0
        self._consecutive_successes = 0
        self._last_state_change = time.time()
        self._metrics.state_changed_at = time.time()

    def _transition_to_open(self):
        """转换到开启状态"""
        logger.warning(f"CircuitBreaker '{self.name}' OPENED (failure_rate={self._metrics.failure_rate:.2%})")
        self._state = CircuitState.OPEN
        self._last_state_change = time.time()
        self._metrics.state_changed_at = time.time()

    def _transition_to_closed(self):
        """转换到关闭状态"""
        logger.info(f"CircuitBreaker '{self.name}' CLOSED (recovered)")
        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._half_open_requests = 0
        self._last_state_change = time.time()
        self._metrics.state_changed_at = time.time()

    def _update_metrics(self, success: bool, response_time: float = 0):
        """更新指标"""
        self._metrics.total_calls += 1

        if success:
            self._metrics.successful_calls += 1
            self._metrics.last_success_time = time.time()
        else:
            self._metrics.failed_calls += 1
            self._metrics.last_failure_time = time.time()

        if response_time > 0:
            self._metrics.recent_response_times.append(response_time)
            times = list(self._metrics.recent_response_times)
            self._metrics.avg_response_time = sum(times) / len(times)

        total = self._metrics.total_calls
        if total > 0:
            self._metrics.success_rate = self._metrics.successful_calls / total
            self._metrics.failure_rate = self._metrics.failed_calls / total

    def _check_failure_threshold(self) -> bool:
        """检查是否达到熔断条件"""
        if self._consecutive_failures >= self.failure_threshold:
            return True

        if (self._metrics.total_calls >= self.min_requests and
            self._metrics.failure_rate > self.failure_rate_threshold):
            return True

        return False

    def allow_request(self) -> bool:
        """判断是否允许请求"""
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._transition_to_half_open()
                    return True
                return False

            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_requests < self.half_open_max_requests:
                    self._half_open_requests += 1
                    return True
                return False

            return False

    def record_success(self, response_time: float = 0):
        """记录成功调用"""
        with self._lock:
            self._update_metrics(success=True, response_time=response_time)

            if self._state == CircuitState.HALF_OPEN:
                self._consecutive_successes += 1
                logger.info(
                    f"CircuitBreaker '{self.name}' HALF_OPEN success "
                    f"({self._consecutive_successes}/{self.success_threshold})"
                )

                if self._consecutive_successes >= self.success_threshold:
                    self._transition_to_closed()

            elif self._state == CircuitState.CLOSED:
                self._consecutive_failures = 0

    def record_failure(self, response_time: float = 0):
        """记录失败调用"""
        with self._lock:
            self._update_metrics(success=False, response_time=response_time)
            self._consecutive_failures += 1

            if self._state == CircuitState.HALF_OPEN:
                logger.warning(f"CircuitBreaker '{self.name}' HALF_OPEN -> OPEN (failed)")
                self._transition_to_open()

            elif self._state == CircuitState.CLOSED:
                if self._check_failure_threshold():
                    self._transition_to_open()

    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """
        异步调用受保护的函数

        Args:
            func: 要调用的异步函数
            *args, **kwargs: 函数参数

        Returns:
            函数返回值

        Raises:
            CircuitBreakerOpenError: 熔断开启时拒绝调用
        """
        if not self.allow_request():
            self._metrics.rejected_calls += 1
            raise CircuitBreakerOpenError(f"CircuitBreaker '{self.name}' is OPEN")

        start_time = time.time()
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            response_time = time.time() - start_time
            self.record_success(response_time)
            return result

        except Exception as e:
            response_time = time.time() - start_time
            self.record_failure(response_time)
            raise

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        同步调用受保护的函数

        Args:
            func: 要调用的函数
            *args, **kwargs: 函数参数

        Returns:
            函数返回值

        Raises:
            CircuitBreakerOpenError: 熔断开启时拒绝调用
        """
        if not self.allow_request():
            self._metrics.rejected_calls += 1
            raise CircuitBreakerOpenError(f"CircuitBreaker '{self.name}' is OPEN")

        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            response_time = time.time() - start_time
            self.record_success(response_time)
            return result

        except Exception as e:
            response_time = time.time() - start_time
            self.record_failure(response_time)
            raise

    def get_status(self) -> dict:
        """获取熔断器状态详情"""
        with self._lock:
            return {
                'name': self.name,
                'state': self._state.value,
                'metrics': {
                    'total_calls': self._metrics.total_calls,
                    'successful_calls': self._metrics.successful_calls,
                    'failed_calls': self._metrics.failed_calls,
                    'rejected_calls': self._metrics.rejected_calls,
                    'success_rate': f"{self._metrics.success_rate:.2%}",
                    'failure_rate': f"{self._metrics.failure_rate:.2%}",
                    'avg_response_time_ms': f"{self._metrics.avg_response_time * 1000:.2f}"
                },
                'consecutive_failures': self._consecutive_failures,
                'consecutive_successes': self._consecutive_successes,
                'time_in_current_state': f"{time.time() - self._last_state_change:.1f}s",
                'half_open_requests': self._half_open_requests
            }


class CircuitBreakerOpenError(Exception):
    """熔断器开启异常"""
    pass


class CircuitBreakerManager:
    """熔断器管理器（统一管理多个熔断器）"""

    def __init__(self):
        self._breakers = {}
        self._lock = Lock()

    def register(self, name: str, **kwargs) -> CircuitBreaker:
        """
        注册熔断器

        Args:
            name: 熔断器名称
            **kwargs: CircuitBreaker初始化参数

        Returns:
            CircuitBreaker实例
        """
        with self._lock:
            if name in self._breakers:
                logger.warning(f"CircuitBreaker '{name}' already registered, returning existing")
                return self._breakers[name]

            breaker = CircuitBreaker(name=name, **kwargs)
            self._breakers[name] = breaker
            logger.info(f"Registered CircuitBreaker '{name}'")
            return breaker

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """获取熔断器"""
        with self._lock:
            return self._breakers.get(name)

    def unregister(self, name: str):
        """注销熔断器"""
        with self._lock:
            if name in self._breakers:
                del self._breakers[name]
                logger.info(f"Unregistered CircuitBreaker '{name}'")

    def get_all_status(self) -> dict:
        """获取所有熔断器状态"""
        with self._lock:
            return {
                name: breaker.get_status()
                for name, breaker in self._breakers.items()
            }

    def get_summary(self) -> dict:
        """获取熔断器汇总信息"""
        with self._lock:
            total_calls = sum(b.metrics.total_calls for b in self._breakers.values())
            total_rejected = sum(b.metrics.rejected_calls for b in self._breakers.values())
            open_count = sum(1 for b in self._breakers.values() if b.state == CircuitState.OPEN)
            half_open_count = sum(1 for b in self._breakers.values() if b.state == CircuitState.HALF_OPEN)

            return {
                'total_breakers': len(self._breakers),
                'total_calls': total_calls,
                'total_rejected': total_rejected,
                'open_count': open_count,
                'half_open_count': half_open_count,
                'closed_count': len(self._breakers) - open_count - half_open_count
            }


_global_circuit_breaker_manager = None


def init_circuit_breaker_manager() -> CircuitBreakerManager:
    """初始化全局熔断器管理器"""
    global _global_circuit_breaker_manager
    _global_circuit_breaker_manager = CircuitBreakerManager()
    return _global_circuit_breaker_manager


def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """获取全局熔断器管理器"""
    global _global_circuit_breaker_manager
    if _global_circuit_breaker_manager is None:
        _global_circuit_breaker_manager = CircuitBreakerManager()
    return _global_circuit_breaker_manager


def get_circuit_breaker(name: str, **kwargs) -> CircuitBreaker:
    """获取或创建熔断器"""
    manager = get_circuit_breaker_manager()
    return manager.get(name) or manager.register(name, **kwargs)
