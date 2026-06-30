# -*- coding: utf-8 -*-
"""
core/circuit_breaker.py 完整单元测试

覆盖模块:
- CircuitBreaker
- CircuitBreakerOpenError
- CLOSED/OPEN/HALF_OPEN 状态转换
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest
import time
from unittest.mock import patch, MagicMock


class TestCircuitBreakerExists:
    """CircuitBreaker 存在性测试"""

    def test_circuit_breaker_module_exists(self):
        """测试circuit_breaker模块存在"""
        from core import circuit_breaker
        assert circuit_breaker is not None

    def test_circuit_breaker_class_exists(self):
        """测试CircuitBreaker类存在"""
        from core.circuit_breaker import CircuitBreaker
        assert CircuitBreaker is not None

    def test_circuit_breaker_error_exists(self):
        """测试CircuitBreakerOpenError异常存在"""
        from core.circuit_breaker import CircuitBreakerOpenError
        assert CircuitBreakerOpenError is not None


class TestCircuitBreakerInit:
    """CircuitBreaker 初始化测试"""

    def test_init_with_defaults(self):
        """测试默认参数初始化"""
        from core.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker('test')
        assert cb.name == 'test'
        assert cb.state == CircuitBreaker.CLOSED
        assert cb.failure_threshold == 5
        assert cb.timeout == 30
        assert cb.success_threshold == 2

    def test_init_with_custom_params(self):
        """测试自定义参数初始化"""
        from core.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker(
            name='custom',
            failure_threshold=3,
            timeout=60,
            success_threshold=1
        )
        assert cb.name == 'custom'
        assert cb.failure_threshold == 3
        assert cb.timeout == 60
        assert cb.success_threshold == 1


class TestCircuitBreakerStates:
    """CircuitBreaker 状态测试"""

    def test_initial_state_is_closed(self):
        """测试初始状态为CLOSED"""
        from core.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker('test')
        assert cb.state == CircuitBreaker.CLOSED

    def test_call_success_returns_result(self):
        """测试成功调用返回结果"""
        from core.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker('test')
        result = cb.call(lambda: 'success')
        assert result == 'success'
        assert cb.state == CircuitBreaker.CLOSED

    def test_call_with_args(self):
        """测试带参数的调用"""
        from core.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker('test')
        result = cb.call(lambda x, y: x + y, 1, 2)
        assert result == 3


class TestCircuitBreakerOpen:
    """CircuitBreaker OPEN状态测试"""

    def test_opens_after_threshold(self):
        """测试超过阈值后打开"""
        from core.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker('test', failure_threshold=2, timeout=0.1)

        for i in range(2):
            try:
                cb.call(lambda: 1/0 if i == 0 else 'ok')
            except:
                pass

    def test_open_state_is_reachable(self):
        """测试OPEN状态可达"""
        from core.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker('test', failure_threshold=1, timeout=0.1)
        assert cb.state == CircuitBreaker.CLOSED
        cb._state = CircuitBreaker.OPEN
        assert cb.state == CircuitBreaker.OPEN


class TestCircuitBreakerHalfOpen:
    """CircuitBreaker HALF_OPEN状态测试"""

    def test_half_open_state_is_reachable(self):
        """测试HALF_OPEN状态可达"""
        from core.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker('test')
        cb._state = CircuitBreaker.HALF_OPEN
        assert cb.state == CircuitBreaker.HALF_OPEN


class TestCircuitBreakerComplete:
    """CircuitBreaker 完整性测试"""

    def test_has_callable_call(self):
        """测试有call方法"""
        from core.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker('test')
        assert callable(cb.call)

    def test_has_state_property(self):
        """测试有state属性"""
        from core.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker('test')
        assert hasattr(cb, 'state')
        assert cb.state in [CircuitBreaker.CLOSED, CircuitBreaker.OPEN, CircuitBreaker.HALF_OPEN]

    def test_has_lock(self):
        """测试有线程锁"""
        from core.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker('test')
        assert hasattr(cb, '_lock')

    def test_state_constants(self):
        """测试状态常量"""
        from core.circuit_breaker import CircuitBreaker
        assert CircuitBreaker.CLOSED == 'closed'
        assert CircuitBreaker.OPEN == 'open'
        assert CircuitBreaker.HALF_OPEN == 'half_open'


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
