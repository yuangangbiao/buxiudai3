# -*- coding: utf-8 -*-
"""
熔断器主系统集成模块

为桌面端提供熔断保护，防止外部API调用级联失败
基于 mobile_api_ai/modules/circuit_breaker.py 封装
"""

import time
import logging
from typing import Callable, Any, Optional, TypeVar, Type
from functools import wraps

from mobile_api_ai.modules.circuit_breaker import (
    CircuitBreaker as OriginalCircuitBreaker,
    CircuitState,
    CircuitMetrics
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitBreakerRegistry:
    """熔断器注册表 - 单例模式"""

    _instance = None
    _lock = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._breakers = {}
            cls._instance._lock = __import__('threading').Lock()
        return cls._instance

    def get_breaker(self, name: str) -> Optional[OriginalCircuitBreaker]:
        """获取指定名称的熔断器"""
        return self._breakers.get(name)

    def register_breaker(self, name: str, breaker: OriginalCircuitBreaker) -> None:
        """注册熔断器"""
        with self._lock:
            self._breakers[name] = breaker
            logger.info(f"熔断器注册: {name}")

    def get_or_create(
        self,
        name: str,
        failure_threshold: int = 50,
        success_threshold: int = 3,
        failure_rate_threshold: float = 0.5,
        open_timeout: float = 30.0,
        recovery_timeout: float = 60.0
    ) -> OriginalCircuitBreaker:
        """获取或创建熔断器"""
        if name in self._breakers:
            return self._breakers[name]

        breaker = OriginalCircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            success_threshold=success_threshold,
            failure_rate_threshold=failure_rate_threshold,
            open_timeout=open_timeout,
            recovery_timeout=recovery_timeout
        )

        with self._lock:
            self._breakers[name] = breaker

        return breaker

    def get_all_breakers(self) -> dict:
        """获取所有熔断器状态"""
        return {
            name: {
                'state': breaker.state.value,
                'metrics': breaker.get_metrics().__dict__
            }
            for name, breaker in self._breakers.items()
        }

    def reset_all(self) -> None:
        """重置所有熔断器"""
        for name, breaker in self._breakers.items():
            breaker.reset()
            logger.info(f"熔断器重置: {name}")


def circuit_protected(
    name: str = "default",
    failure_threshold: int = 50,
    success_threshold: int = 3,
    failure_rate_threshold: float = 0.5,
    open_timeout: float = 30.0,
    recovery_timeout: float = 60.0,
    fallback: Optional[Callable[..., Any]] = None
):
    """
    熔断保护装饰器

    Args:
        name: 熔断器名称
        failure_threshold: 连续失败次数阈值
        success_threshold: 连续成功次数阈值
        failure_rate_threshold: 失败率阈值
        open_timeout: 熔断超时时间（秒）
        recovery_timeout: 恢复超时时间（秒）
        fallback: 降级函数，当熔断开启时调用

    Usage:
        @circuit_protected("wechat_api", fallback=wechat_fallback)
        def send_wechat_message(msg):
            ...

        def wechat_fallback(msg):
            return {"status": "fallback", "message": "服务暂时不可用"}
    """
    registry = CircuitBreakerRegistry()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        breaker = registry.get_or_create(
            name=name,
            failure_threshold=failure_threshold,
            success_threshold=success_threshold,
            failure_rate_threshold=failure_rate_threshold,
            open_timeout=open_timeout,
            recovery_timeout=recovery_timeout
        )

        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            if breaker.state == CircuitState.OPEN:
                logger.warning(f"[CircuitBreaker:{name}] 熔断开启，拒绝请求")
                if fallback:
                    logger.info(f"[CircuitBreaker:{name}] 执行降级函数")
                    return fallback(*args, **kwargs)
                raise CircuitBreakerOpenError(f"熔断器 {name} 已开启")

            try:
                result = func(*args, **kwargs)
                breaker.record_success()
                return result
            except Exception as e:
                breaker.record_failure()
                logger.error(f"[CircuitBreaker:{name}] 调用失败: {e}")
                if fallback:
                    return fallback(*args, **kwargs)
                raise

        wrapper.breaker = breaker
        wrapper.name = name
        return wrapper

    return decorator


class CircuitBreakerOpenError(Exception):
    """熔断器开启异常"""
    pass


class CircuitBreakerManager:
    """熔断器管理器 - 提供便捷的熔断控制接口"""

    def __init__(self):
        self.registry = CircuitBreakerRegistry()

    def protect(
        self,
        name: str,
        func: Callable[..., T],
        *args,
        fallback: Optional[Callable[..., Any]] = None,
        **kwargs
    ) -> T:
        """
        保护函数调用

        Args:
            name: 熔断器名称
            func: 要保护的函数
            *args: 函数参数
            fallback: 降级函数
            **kwargs: 函数关键字参数

        Returns:
            函数执行结果
        """
        breaker = self.registry.get_or_create(name)

        if breaker.state == CircuitState.OPEN:
            if fallback:
                return fallback(*args, **kwargs)
            raise CircuitBreakerOpenError(f"熔断器 {name} 已开启")

        try:
            result = func(*args, **kwargs)
            breaker.record_success()
            return result
        except Exception as e:
            breaker.record_failure()
            if fallback:
                return fallback(*args, **kwargs)
            raise

    def get_status(self, name: str) -> Optional[dict]:
        """获取熔断器状态"""
        breaker = self.registry.get_breaker(name)
        if not breaker:
            return None

        return {
            'name': name,
            'state': breaker.state.value,
            'metrics': breaker.get_metrics().__dict__
        }

    def get_all_status(self) -> dict:
        """获取所有熔断器状态"""
        return self.registry.get_all_breakers()

    def is_available(self, name: str) -> bool:
        """检查熔断器是否可用（未熔断）"""
        breaker = self.registry.get_breaker(name)
        if not breaker:
            return True
        return breaker.state != CircuitState.OPEN


def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """获取熔断器管理器单例"""
    return CircuitBreakerManager()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    manager = CircuitBreakerManager()

    @circuit_protected("test_api", fallback=lambda: {"status": "fallback"})
    def test_api_call(data):
        if time.time() % 3 < 1:
            raise ConnectionError("模拟网络错误")
        return {"status": "success", "data": data}

    print("=" * 60)
    print("熔断器集成模块测试")
    print("=" * 60)

    for i in range(10):
        result = test_api_call(f"请求{i+1}")
        status = manager.get_status("test_api")
        print(f"请求{i+1}: {result} | 熔断状态: {status['state']}")

    print("\n" + "=" * 60)
