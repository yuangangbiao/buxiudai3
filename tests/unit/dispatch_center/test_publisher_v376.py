# -*- coding: utf-8 -*-
"""
[v3.7.6] publisher.py 新功能单元测试

覆盖:
- QualityPublisher
- CircuitBreaker
- get_all_tasks / get_task_by_id / get_task_count
- is_available 属性
"""
import pytest
from unittest.mock import MagicMock, patch
import importlib
import sys
import importlib.util
import os


def _load_publisher():
    """直接加载 publisher 模块"""
    if 'mobile_api_ai.dispatch_center.publisher' in sys.modules:
        return sys.modules['mobile_api_ai.dispatch_center.publisher']
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        'mobile_api_ai', 'dispatch_center', 'publisher.py'
    )
    spec = importlib.util.spec_from_file_location("publisher_v376", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope='module')
def pub():
    """加载 publisher 模块"""
    return _load_publisher()


class TestQualityPublisher:
    """QualityPublisher 测试（v3.7.6 新增）"""

    def test_quality_publisher_exists(self, pub):
        """QualityPublisher 类存在"""
        assert hasattr(pub, 'QualityPublisher')

    def test_get_quality_publisher(self, pub):
        """get_publisher('quality')"""
        p = pub.get_publisher('quality')
        assert p is not None
        assert p.name == 'quality'

    def test_quality_publish(self, pub):
        """quality publish 方法"""
        p = pub.get_publisher('quality')
        result = p.publish({'order_no': 'WO-Q-001', 'check_type': 'visual'})
        assert result is True


class TestCircuitBreaker:
    """CircuitBreaker 测试（v3.7.6 新增）"""

    def test_circuit_breaker_class_exists(self, pub):
        """CircuitBreaker 类存在"""
        assert hasattr(pub, 'CircuitBreaker')

    def test_circuit_breaker_initial_state(self, pub):
        """初始状态 CLOSED"""
        cb = pub.CircuitBreaker(failure_threshold=3)
        status = cb.get_status()
        assert status['state'] == 'CLOSED'
        assert status['failures'] == 0

    def test_circuit_breaker_call_success(self, pub):
        """成功调用"""
        cb = pub.CircuitBreaker()
        result = cb.call(lambda: 'ok')
        assert result == 'ok'

    def test_circuit_breaker_failure_threshold(self, pub):
        """失败次数达到阈值进入 OPEN"""
        cb = pub.CircuitBreaker(failure_threshold=2, recovery_timeout=60)
        def failing():
            raise RuntimeError('fail')
        # 触发 2 次失败
        for _ in range(2):
            try:
                cb.call(failing)
            except RuntimeError:
                pass
        # 状态应该是 OPEN
        assert cb.get_status()['state'] == 'OPEN'

    def test_circuit_breaker_rejects_when_open(self, pub):
        """OPEN 状态拒绝请求"""
        cb = pub.CircuitBreaker(failure_threshold=1)
        def failing():
            raise RuntimeError('fail')
        try:
            cb.call(failing)
        except RuntimeError:
            pass
        # OPEN 后调用应抛 RuntimeError
        with pytest.raises(RuntimeError, match='熔断器'):
            cb.call(lambda: 'ok')


class TestTaskQueryMethods:
    """任务查询方法测试（v3.7.6 新增）"""

    def test_get_all_tasks_empty(self, pub):
        """初始无任务"""
        # 重置（仅测试用）
        pub._task_store.clear()
        assert pub.get_all_tasks() == []

    def test_store_and_get_task(self, pub):
        """存储 + 查询任务"""
        pub._task_store.clear()
        pub._store_task('T001', 'report', {'order_no': 'WO-001'})
        task = pub.get_task_by_id('T001')
        assert task is not None
        assert task['id'] == 'T001'
        assert task['type'] == 'report'

    def test_get_task_by_id_not_found(self, pub):
        """查询不存在的任务"""
        assert pub.get_task_by_id('NONEXISTENT') is None

    def test_get_task_count_empty(self, pub):
        """统计为空"""
        pub._task_store.clear()
        count = pub.get_task_count()
        assert count['total'] == 0

    def test_get_task_count_with_data(self, pub):
        """统计有数据"""
        pub._task_store.clear()
        pub._store_task('T001', 'report', {})
        pub._store_task('T002', 'material', {})
        pub._store_task('T003', 'report', {})
        count = pub.get_task_count()
        assert count['total'] == 3
        assert count['report'] == 2
        assert count['material'] == 1


class TestIsAvailable:
    """is_available 属性测试"""

    def test_report_publisher_available(self, pub):
        """report publisher 默认可用"""
        p = pub.get_publisher('report')
        assert p.is_available is True

    def test_quality_publisher_available(self, pub):
        """quality publisher 默认可用"""
        p = pub.get_publisher('quality')
        assert p.is_available is True

    def test_unavailable_when_circuit_open(self, pub):
        """熔断器 OPEN 时不可用"""
        p = pub.get_publisher('report')
        # 强制设置熔断器为 OPEN
        p._circuit_breaker._state = 'OPEN'
        assert p.is_available is False


class TestGetCircuitBreakerStatus:
    """熔断器状态查询"""

    def test_get_circuit_breaker_status(self, pub):
        """获取熔断器状态"""
        p = pub.get_publisher('report')
        status = p.get_circuit_breaker_status()
        assert 'state' in status
        assert 'failures' in status
        assert 'threshold' in status