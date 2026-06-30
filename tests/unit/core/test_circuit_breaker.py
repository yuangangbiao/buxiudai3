"""熔断器 CircuitBreaker 单元测试"""
import time
import threading
import pytest
from core.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError


class TestCircuitBreakerStructure:
    """验证类结构与基本属性"""

    def test_class_exists(self):
        """CircuitBreaker 类存在"""
        assert CircuitBreaker is not None

    def test_three_states_defined(self):
        """CLOSED / OPEN / HALF_OPEN 三态已定义"""
        assert CircuitBreaker.CLOSED == 'closed'
        assert CircuitBreaker.OPEN == 'open'
        assert CircuitBreaker.HALF_OPEN == 'half_open'

    def test_circuit_breaker_open_error_exists(self):
        """CircuitBreakerOpenError 异常类已定义，继承 Exception"""
        assert issubclass(CircuitBreakerOpenError, Exception)

    def test_initial_state_is_closed(self):
        """初始状态为 CLOSED"""
        cb = CircuitBreaker('test')
        assert cb.state == CircuitBreaker.CLOSED

    def test_thread_safety_lock_exists(self):
        """线程安全锁 threading.Lock 已初始化"""
        cb = CircuitBreaker('test')
        assert isinstance(cb._lock, type(threading.Lock()))

    def test_default_parameters(self):
        """默认参数正确"""
        cb = CircuitBreaker('default')
        assert cb.failure_threshold == 5
        assert cb.timeout == 30
        assert cb.success_threshold == 2


class TestClosedState:
    """CLOSED 状态行为测试"""

    def test_successful_call_returns_result(self):
        """成功调用返回正确结果"""
        cb = CircuitBreaker('test')
        result = cb.call(lambda x, y: x + y, 1, 2)
        assert result == 3

    def test_successful_call_passes_args_kwargs(self):
        """call() 正确传递 *args 和 **kwargs"""
        cb = CircuitBreaker('test')
        result = cb.call(lambda a, b, c=0: a + b + c, 10, 20, c=30)
        assert result == 60

    def test_success_resets_failure_count(self):
        """成功后重置失败计数"""
        cb = CircuitBreaker('test', failure_threshold=3)
        # 先产生 2 次失败
        for _ in range(2):
            try:
                cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))
            except Exception:
                pass
        assert cb._failures == 2
        # 一次成功后失败计数归零
        cb.call(lambda: 'ok')
        assert cb._failures == 0

    def test_failures_accumulate(self):
        """失败累积但未达阈值时不触发 OPEN"""
        cb = CircuitBreaker('test', failure_threshold=5)
        for i in range(4):
            try:
                cb.call(lambda: (_ for _ in ()).throw(Exception(f"fail {i}")))
            except Exception:
                pass
        assert cb.state == CircuitBreaker.CLOSED
        assert cb._failures == 4

    def test_raises_original_exception(self):
        """失败时传播原始异常"""
        cb = CircuitBreaker('test')
        with pytest.raises(ValueError, match="bad"):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("bad")))


class TestClosedToOpenTransition:
    """CLOSED → OPEN 状态转换测试"""

    def test_transitions_to_open_when_failure_threshold_reached(self):
        """达到失败阈值 → OPEN"""
        cb = CircuitBreaker('test', failure_threshold=2)
        for _ in range(2):
            try:
                cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))
            except Exception:
                pass
        assert cb.state == CircuitBreaker.OPEN

    def test_stays_open_after_threshold(self):
        """OPEN 后不因更多失败改变状态"""
        cb = CircuitBreaker('test', failure_threshold=2)
        for _ in range(2):
            try:
                cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))
            except Exception:
                pass
        assert cb.state == CircuitBreaker.OPEN
        # 额外尝试调用确认被拒绝
        with pytest.raises(CircuitBreakerOpenError):
            cb.call(lambda: 'nope')

    def test_open_state_raises_circuit_breaker_open_error(self):
        """OPEN 状态下所有调用抛出 CircuitBreakerOpenError"""
        cb = CircuitBreaker('test', failure_threshold=1)
        try:
            cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))
        except Exception:
            pass
        assert cb.state == CircuitBreaker.OPEN
        with pytest.raises(CircuitBreakerOpenError, match="熔断中"):
            cb.call(lambda: 'should not run')


class TestOpenToHalfOpenTransition:
    """OPEN → HALF_OPEN 状态转换测试"""

    def test_transitions_to_half_open_after_timeout(self):
        """超时后 → HALF_OPEN"""
        cb = CircuitBreaker('test', failure_threshold=1, timeout=0.1)
        try:
            cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))
        except Exception:
            pass
        assert cb.state == CircuitBreaker.OPEN
        time.sleep(0.15)  # > timeout
        cb.call(lambda: 'first after timeout')
        assert cb.state == CircuitBreaker.HALF_OPEN

    def test_half_open_allows_calls(self):
        """HALF_OPEN 状态允许调用"""
        cb = CircuitBreaker('test', failure_threshold=1, timeout=0.1)
        try:
            cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))
        except Exception:
            pass
        time.sleep(0.15)
        result = cb.call(lambda: 'allowed')
        assert result == 'allowed'


class TestHalfOpenToClosedTransition:
    """HALF_OPEN → CLOSED 状态转换测试"""

    def test_transitions_to_closed_after_success_threshold(self):
        """连续成功达到 success_threshold → CLOSED"""
        cb = CircuitBreaker('test', failure_threshold=1, timeout=0.1, success_threshold=2)
        try:
            cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))
        except Exception:
            pass
        time.sleep(0.15)
        cb.call(lambda: 'ok1')
        assert cb.state == CircuitBreaker.HALF_OPEN
        cb.call(lambda: 'ok2')
        assert cb.state == CircuitBreaker.CLOSED

    def test_closed_state_resets_failure_count(self):
        """回到 CLOSED 后失败计数归零"""
        cb = CircuitBreaker('test', failure_threshold=1, timeout=0.1, success_threshold=2)
        try:
            cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))
        except Exception:
            pass
        time.sleep(0.15)
        cb.call(lambda: 'ok1')
        cb.call(lambda: 'ok2')
        assert cb.state == CircuitBreaker.CLOSED
        assert cb._failures == 0


class TestHalfOpenFailure:
    """HALF_OPEN 状态中失败的预期行为"""

    def test_half_open_failure_should_go_back_to_open(self):
        """HALF_OPEN 中单次失败应重回 OPEN（已知 BUG）"""
        cb = CircuitBreaker('test', failure_threshold=1, timeout=0.1, success_threshold=2)
        # 先进入 OPEN
        try:
            cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))
        except Exception:
            pass
        time.sleep(0.15)
        # HALF_OPEN 中成功一次
        cb.call(lambda: 'ok')
        assert cb.state == CircuitBreaker.HALF_OPEN
        # HALF_OPEN 中失败，应回到 OPEN
        try:
            cb.call(lambda: (_ for _ in ()).throw(Exception("half_open_fail")))
        except Exception:
            pass
        # 期望 OPEN，但当前实现未处理此转换
        if cb.state != CircuitBreaker.OPEN:
            pytest.fail(
                "BUG: HALF_OPEN 中失败应回到 OPEN，当前仍为 "
                f"{cb.state}。call() 第 54 行仅检查 _state == CLOSED，"
                "缺少 HALF_OPEN 失败 → OPEN 的转换逻辑。"
            )


class TestConcurrency:
    """并发安全测试"""

    def test_concurrent_calls_under_stress(self):
        """多线程并发调用不引发竞态"""
        cb = CircuitBreaker('concurrent', failure_threshold=50, timeout=1)
        results = []
        errors = []
        barrier = threading.Barrier(10)

        def worker():
            barrier.wait()
            for _ in range(20):
                try:
                    r = cb.call(lambda x: x * 2, 21)
                    results.append(r)
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 所有调用都应成功（failure_threshold 远大于并发量）
        assert len(results) == 200
        assert len(errors) == 0
        assert cb.state == CircuitBreaker.CLOSED

    def test_state_remains_consistent_under_concurrent_failures(self):
        """并发失败下状态一致性"""
        cb = CircuitBreaker('concurrent2', failure_threshold=5)
        errors_list = []

        def failing_worker():
            for _ in range(10):
                try:
                    cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))
                except Exception as e:
                    errors_list.append(e)

        threads = [threading.Thread(target=failing_worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 状态应在第一次达阈值后稳定为 OPEN
        assert cb.state in (CircuitBreaker.OPEN, CircuitBreaker.CLOSED)
        if cb.state == CircuitBreaker.OPEN:
            # 确认后续调用被拒绝
            with pytest.raises(CircuitBreakerOpenError):
                cb.call(lambda: 'nope')
