# -*- coding: utf-8 -*-
"""core/event_bus_factory.py 完整测试——事件总线工厂"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock


class TestCreateEventBus:
    """create_event_bus 路由——Redis / Inprocess"""

    def test_default_inprocess(self):
        from core.event_bus_factory import create_event_bus
        mock_instance = MagicMock()
        # mock sync 模块树，让 from sync.event_bus import EventBus 成功
        mock_sync = MagicMock()
        mock_sync.event_bus.EventBus.get.return_value = mock_instance
        with patch('core.event_bus_factory.os.getenv', return_value='inprocess'):
            with patch.dict('sys.modules', {'sync': mock_sync, 'sync.event_bus': mock_sync.event_bus}):
                bus = create_event_bus()
                assert bus == mock_instance

    def test_unknown_backend_falls_to_inprocess(self):
        from core.event_bus_factory import create_event_bus
        mock_instance = MagicMock()
        mock_sync = MagicMock()
        mock_sync.event_bus.EventBus.get.return_value = mock_instance
        with patch('core.event_bus_factory.os.getenv', side_effect=lambda k, d=None: {
            'EVENT_BUS_BACKEND': 'kafka',
        }.get(k, d)):
            with patch.dict('sys.modules', {'sync': mock_sync, 'sync.event_bus': mock_sync.event_bus}):
                bus = create_event_bus()
                assert bus == mock_instance

    def test_redis_backend_success(self):
        from core.event_bus_factory import create_event_bus
        mock_redis_bus = MagicMock()
        with patch('core.event_bus_factory.os.getenv', side_effect=lambda k, d=None: {
            'EVENT_BUS_BACKEND': 'redis',
            'REDIS_HOST': 'rhost',
            'REDIS_PORT': '6380',
        }.get(k, d)):
            with patch('core.redis_event_bus.RedisEventBus', return_value=mock_redis_bus) as MockRedis:
                bus = create_event_bus()
                assert bus == mock_redis_bus
                MockRedis.assert_called_once_with(host='rhost', port=6380)

    def test_redis_backend_fallback(self):
        """Redis 不可用时应降级到 inprocess"""
        from core.event_bus_factory import create_event_bus
        mock_instance = MagicMock()
        mock_sync = MagicMock()
        mock_sync.event_bus.EventBus.get.return_value = mock_instance
        with patch('core.event_bus_factory.os.getenv', side_effect=lambda k, d=None: {
            'EVENT_BUS_BACKEND': 'redis',
            'REDIS_HOST': 'localhost',
            'REDIS_PORT': '6379',
        }.get(k, d)):
            with patch('core.redis_event_bus.RedisEventBus', side_effect=Exception("no redis")):
                with patch.dict('sys.modules', {'sync': mock_sync, 'sync.event_bus': mock_sync.event_bus}):
                    bus = create_event_bus()
                    assert bus == mock_instance

    def test_redis_backend_default_host_port(self):
        from core.event_bus_factory import create_event_bus
        mock_redis_bus = MagicMock()
        with patch('core.event_bus_factory.os.getenv', side_effect=lambda k, d=None: {
            'EVENT_BUS_BACKEND': 'redis',
        }.get(k, d)):
            with patch('core.redis_event_bus.RedisEventBus', return_value=mock_redis_bus) as MockRedis:
                bus = create_event_bus()
                MockRedis.assert_called_once_with(host='localhost', port=6379)

    def test_sync_event_bus_fallback(self):
        """先尝试 sync.event_bus.EventBus，导入失败则用 core.event_bus.EventBus"""
        from core.event_bus_factory import create_event_bus
        mock_instance = MagicMock()
        with patch('core.event_bus_factory.os.getenv', return_value='inprocess'):
            # 让 sync.event_bus 导入失败，触发 fallback 到 core.event_bus.EventBus
            with patch('core.event_bus.EventBus', return_value=mock_instance) as MockBus:
                with patch.dict('sys.modules', {'sync.event_bus': None}):
                    bus = create_event_bus()
                    assert bus == mock_instance
