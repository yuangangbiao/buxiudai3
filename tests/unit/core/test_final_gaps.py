# -*- coding: utf-8 -*-
"""最后缺口填补: event_store(96%→100%) + metrics(94%→100%) + feature_flags(94%→100%)
validators(99%→100%) 通过修复源码实现"""
import pytest
from unittest.mock import patch, MagicMock


# ============================================================
# event_store: 覆盖 _connection_factory=None 的 fallback 路径（L16-17）
# ============================================================
class TestEventStoreFallback:
    def test_get_conn_without_factory(self):
        from core.event_store import _get_conn, set_connection_factory
        # 清除 factory，强制走 fallback
        import core.event_store
        core.event_store._connection_factory = None

        mock_conn = MagicMock()
        with patch('models.database.get_connection', return_value=mock_conn):
            conn = _get_conn()
            assert conn is mock_conn

    def test_set_factory_and_get_conn(self):
        from core.event_store import _get_conn, set_connection_factory
        mock_conn = MagicMock()
        set_connection_factory(lambda: mock_conn)
        assert _get_conn() is mock_conn


# ============================================================
# metrics: 覆盖 record_metric() 和 record_latency() 模块级函数（L44,47）
# ============================================================
class TestMetricsModuleFunctions:
    def test_record_metric_calls_global(self):
        from core.metrics import record_metric, _metrics
        prev = _metrics._counters.get('test:fix', 0)
        record_metric('test:fix', 5)
        assert _metrics._counters['test:fix'] == prev + 5

    def test_record_latency_calls_global(self):
        from core.metrics import record_latency, _metrics
        record_latency('test:api', 42)
        assert 42 in _metrics._histograms.get('test:api', [])


# ============================================================
# feature_flags: 覆盖 get_all() 返回 dict（L53）
# ============================================================
class TestFeatureFlagsAll:
    def test_all_returns_dict(self):
        from core.feature_flags import FeatureFlags
        FeatureFlags._flags = {'ai_report': True, 'beta': False}
        result = FeatureFlags.all()
        assert isinstance(result, dict)
        assert result['ai_report'] is True
        assert result['beta'] is False

    def test_all_empty(self):
        from core.feature_flags import FeatureFlags
        FeatureFlags._flags = {}
        assert FeatureFlags.all() == {}


# ============================================================
# validators: adjustment=0 现在可正确触发（修复源码后）
# ============================================================
class TestInventoryAdjustmentZeroFixed:
    def test_adjustment_zero_after_fix(self):
        from utils.validators import InventoryValidator
        with pytest.raises(Exception, match="不能为0"):
            InventoryValidator.validate_adjustment({"adjustment": 0})
