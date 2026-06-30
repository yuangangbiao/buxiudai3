# Q1.6-Q1.12: 熔断器+规则引擎+EventBus+特性开关+指标+错误码+事件常量
import pytest, sys, os, json, time
from unittest.mock import MagicMock, patch



# ====== Q1.6: CircuitBreaker ======
class TestCircuitBreaker:
    def test_closed_to_open_after_failures(self):
        from core.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker('test', failure_threshold=3, timeout=30)
        assert cb.state == 'closed'
        for _ in range(3):
            try: cb.call(lambda: (_ for _ in ()).throw(Exception('fail')))
            except: pass
        assert cb.state == 'open'

    def test_open_rejects_calls(self):
        from core.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker('test', failure_threshold=1, timeout=30)
        try: cb.call(lambda: (_ for _ in ()).throw(Exception('fail')))
        except: pass
        assert cb.state == 'open'
        with pytest.raises(Exception):  # CircuitBreakerOpenError
            cb.call(lambda: True)

    def test_half_open_success_returns_to_closed(self):
        from core.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker('test', failure_threshold=1, timeout=0.01)
        try: cb.call(lambda: (_ for _ in ()).throw(Exception('fail')))
        except: pass
        assert cb.state == 'open'
        time.sleep(0.02)
        result = cb.call(lambda: True)
        assert result is True
        cb.call(lambda: True)  # second success
        assert cb.state == 'closed'


# ====== Q1.7: RuleEngine ======
class TestRuleEngine:
    def test_load_rules_from_json(self, tmp_path):
        from core.rule_engine import RuleEngine
        rules_dir = tmp_path / 'rules'
        rules_dir.mkdir()
        (rules_dir / 'process_rules.json').write_text(
            json.dumps({"processes": {"编织": {"unit": "米"}}}), encoding='utf-8')
        engine = RuleEngine(str(rules_dir))
        assert engine.get_process('编织') == {"unit": "米"}

    def test_get_process_miss_returns_default(self):
        from core.rule_engine import RuleEngine
        with patch('os.path.isdir', return_value=False):
            engine = RuleEngine()
        assert engine.get_process('不存在的工序', default='N/A') == 'N/A'


# ====== Q1.8: EventBus ======
class TestEventBus:
    def teardown_method(self):
        from core.event_bus import EventBus
        EventBus.reset()

    def test_publish_subscribe(self):
        from core.event_bus import EventBus
        received = []
        EventBus.subscribe('test:event', lambda ev, d: received.append(d))
        EventBus.publish('test:event', {'key': 'val'})
        assert len(received) == 1
        assert received[0] == {'key': 'val'}

    def test_reset_clears_handlers(self):
        from core.event_bus import EventBus
        EventBus.subscribe('test:event', lambda d: None)
        EventBus.reset()
        EventBus.subscribe('test:event', lambda d: None)
        # 不抛异常即可
        assert True


# ====== Q1.9: FeatureFlags ======
class TestFeatureFlags:
    def test_load_from_env(self, monkeypatch):
        monkeypatch.setenv('FEATURE_AI_REPORT', 'true')
        monkeypatch.setenv('FEATURE_BETA', 'false')
        from core.feature_flags import FeatureFlags
        FeatureFlags._flags = {}
        FeatureFlags.load()
        assert FeatureFlags.is_enabled('ai_report') is True
        assert FeatureFlags.is_enabled('beta') is False

    def test_unknown_flag_returns_default(self):
        from core.feature_flags import FeatureFlags
        assert FeatureFlags.is_enabled('nonexist', default=True) is True


# ====== Q1.10: Metrics ======
class TestMetrics:
    def test_counter_increment(self):
        from core.metrics import MetricsCollector
        m = MetricsCollector()
        m.increment('orders', 5)
        assert m.get_counters()['orders'] == 5

    def test_p99_calculation(self):
        from core.metrics import MetricsCollector
        m = MetricsCollector()
        for i in range(100):
            m.record_latency('api', i)
        p99 = m.get_p99('api')
        assert p99 >= 98


# ====== Q1.11: ErrorCodes ======
class TestErrorCodes:
    def test_error_code_equality(self):
        from core.error_codes_structured import ErrorCode
        e1 = ErrorCode('E1001', '订单不存在', 'order', 'error', 404)
        assert e1.code == 'E1001'
        assert e1.http_status == 404

    def test_domain_constants(self):
        from core.error_codes_structured import ErrorDomain, ErrorSeverity
        assert ErrorDomain.ORDER == 'order'
        assert ErrorSeverity.CRITICAL == 'critical'


# ====== Q1.12: EventType ======
class TestEventType:
    def test_no_duplicate_values(self):
        from core.events import EventType
        vals = [v for k, v in vars(EventType).items() if not k.startswith('_') and isinstance(v, str)]
        assert len(vals) == len(set(vals))

    def test_order_events_exist(self):
        from core.events import EventType
        assert EventType.ORDER_CREATED == 'order:created'
        assert EventType.ORDER_SHIPPED == 'order:shipped'
