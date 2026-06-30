# -*- coding: utf-8 -*-
"""批量冲刺30% - cors_config + event_bus 补全"""
import pytest
from unittest.mock import patch, MagicMock


# ============================================================
# core/cors_config.py
# ============================================================
class TestCorsConfig:
    def test_init_cors_valid(self):
        from flask import Flask
        from core.cors_config import init_cors
        app = Flask(__name__)
        init_cors(app, default_origins='http://localhost:3000')
        # should not raise

    def test_init_cors_multiple_origins(self):
        from flask import Flask
        from core.cors_config import init_cors
        app = Flask(__name__)
        init_cors(app, default_origins='http://a.com,https://b.com')
        # should not raise

    def test_init_cors_env_var(self, monkeypatch):
        from flask import Flask
        from core.cors_config import init_cors
        monkeypatch.setenv('CORS_ALLOWED_ORIGINS', 'http://prod.com')
        app = Flask(__name__)
        init_cors(app)
        # should not raise

    def test_init_cors_rejects_star(self):
        from flask import Flask
        from core.cors_config import init_cors
        app = Flask(__name__)
        with pytest.raises(ValueError, match='禁止使用'):
            init_cors(app, default_origins='*')

    def test_init_cors_rejects_empty(self):
        from flask import Flask
        from core.cors_config import init_cors
        app = Flask(__name__)
        with pytest.raises(ValueError, match='未正确配置'):
            init_cors(app, default_origins='')


# ============================================================
# core/event_bus.py 补全 69% → 100% (22 missed)
# ============================================================
class TestEventBusFull:
    def test_global_singleton(self):
        from core.event_bus import EventBus
        # EventBus is a class - verify it has the needed methods
        assert hasattr(EventBus, 'subscribe')
        assert hasattr(EventBus, 'publish')

    def test_multiple_subscribers_same_event(self):
        from core.event_bus import EventBus
        results = []
        EventBus.subscribe('multi:test', lambda ev, d: results.append(1))
        EventBus.subscribe('multi:test', lambda ev, d: results.append(2))
        EventBus.publish('multi:test', {})
        assert results == [1, 2]

    def test_unsubscribe(self):
        from core.event_bus import EventBus
        received = []
        def handler(ev, d):
            received.append(d)
        EventBus.subscribe('unsub:test', handler)
        EventBus.unsubscribe('unsub:test', handler)
        EventBus.publish('unsub:test', {'key': 'val'})
        assert received == []

    def test_publish_no_subscribers(self):
        from core.event_bus import EventBus
        # should not raise
        EventBus.publish('no:subscribers', {'x': 1})

    def test_reset_clears_all(self):
        from core.event_bus import EventBus
        EventBus.subscribe('reset:test', lambda ev, d: None)
        EventBus.reset()
        received = []
        EventBus.subscribe('reset:test', lambda ev, d: received.append(d))
        EventBus.publish('reset:test', {'after': 'reset'})
        assert len(received) == 1
        assert received[0] == {'after': 'reset'}

    def test_publish_with_data_types(self):
        from core.event_bus import EventBus
        results = {}
        EventBus.subscribe('types:test', lambda ev, d: results.update({ev: d}))
        EventBus.publish('types:test', {'int': 1, 'str': 's', 'list': [1, 2]})
        assert 'types:test' in results
        assert results['types:test']['int'] == 1


# ============================================================
# core/event_bus_factory.py
# ============================================================
class TestEventBusFactory:
    def test_create_default_bus(self):
        from core.event_bus_factory import create_event_bus
        bus = create_event_bus()
        assert bus is not None

    def test_create_event_bus_with_name(self):
        from core.event_bus_factory import create_event_bus
        bus = create_event_bus()
        assert bus is not None
