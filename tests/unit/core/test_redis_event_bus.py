# -*- coding: utf-8 -*-
"""core/redis_event_bus.py 完整测试——Redis Pub/Sub 跨进程事件总线 + 内存降级"""

import json
import threading
import pytest
from unittest.mock import patch, MagicMock, call


class TestRedisEventBusInit:
    """RedisEventBus 初始化——Redis可用/不可用"""

    def test_init_redis_available(self):
        from core import redis_event_bus as reb_module
        from core.redis_event_bus import RedisEventBus
        fake_redis_mod = MagicMock()
        with patch.object(reb_module, 'REDIS_AVAILABLE', True):
            with patch.object(reb_module, 'redis', fake_redis_mod):
                bus = RedisEventBus(host='myhost', port=6380, db=1)
                assert bus._host == 'myhost'
                assert bus._port == 6380
                assert bus._db == 1
                assert bus._redis == fake_redis_mod.Redis.return_value
                fake_redis_mod.Redis.return_value.ping.assert_called_once()

    def test_init_redis_unavailable(self):
        from core import redis_event_bus as reb_module
        from core.redis_event_bus import RedisEventBus
        fake_redis_mod = MagicMock()
        fake_redis_mod.Redis.side_effect = Exception("no redis")
        with patch.object(reb_module, 'REDIS_AVAILABLE', True):
            with patch.object(reb_module, 'redis', fake_redis_mod):
                bus = RedisEventBus()
                assert bus._redis is None

    def test_init_redis_ping_fails(self):
        from core import redis_event_bus as reb_module
        from core.redis_event_bus import RedisEventBus
        fake_redis_mod = MagicMock()
        fake_redis_mod.Redis.return_value.ping.side_effect = Exception("ping fail")
        with patch.object(reb_module, 'REDIS_AVAILABLE', True):
            with patch.object(reb_module, 'redis', fake_redis_mod):
                bus = RedisEventBus()
                assert bus._redis is None

    def test_init_redis_not_installed(self):
        from core.redis_event_bus import RedisEventBus
        with patch('core.redis_event_bus.REDIS_AVAILABLE', False):
            bus = RedisEventBus()
            assert bus._redis is None

    def test_init_defaults(self):
        from core.redis_event_bus import RedisEventBus
        with patch('core.redis_event_bus.REDIS_AVAILABLE', False):
            bus = RedisEventBus()
        assert bus._host == 'localhost'
        assert bus._port == 6379
        assert bus._db == 0
        assert bus._channel == 'steelbelt:events'


class TestRedisEventBusPublish:
    """publish 方法——Redis 推送 + 内存降级分发"""

    def test_publish_with_redis(self):
        from core.redis_event_bus import RedisEventBus
        mock_redis = MagicMock()
        bus = RedisEventBus()
        bus._redis = mock_redis
        bus._subscribers = {}
        bus.publish('order.created', {'id': 1})
        expected = json.dumps({'event': 'order.created', 'data': {'id': 1}}, ensure_ascii=False, default=str)
        mock_redis.publish.assert_called_once_with('steelbelt:events', expected)

    def test_publish_with_redis_failure(self):
        from core.redis_event_bus import RedisEventBus
        mock_redis = MagicMock()
        mock_redis.publish.side_effect = Exception("publish fail")
        bus = RedisEventBus()
        bus._redis = mock_redis
        bus._subscribers = {}
        # 不应抛出异常
        bus.publish('order.created', {'id': 1})
        mock_redis.publish.assert_called_once()

    def test_publish_without_redis(self):
        from core.redis_event_bus import RedisEventBus
        bus = RedisEventBus()
        bus._redis = None
        handler = MagicMock()
        bus._subscribers = {'order.created': [handler]}
        bus.publish('order.created', {'id': 42})
        handler.assert_called_once_with({'id': 42})

    def test_publish_multiple_handlers(self):
        from core.redis_event_bus import RedisEventBus
        bus = RedisEventBus()
        bus._redis = None
        h1 = MagicMock()
        h2 = MagicMock()
        bus._subscribers = {'event_x': [h1, h2]}
        bus.publish('event_x', 'data')
        h1.assert_called_once_with('data')
        h2.assert_called_once_with('data')

    def test_publish_no_subscribers(self):
        from core.redis_event_bus import RedisEventBus
        bus = RedisEventBus()
        bus._redis = None
        bus._subscribers = {}
        # 不应报错
        bus.publish('no_such_event', {})

    def test_publish_handler_raises(self):
        from core.redis_event_bus import RedisEventBus
        bus = RedisEventBus()
        bus._redis = None
        handler_ok = MagicMock()
        handler_bad = MagicMock(side_effect=ValueError("handler fail"))
        bus._subscribers = {'evt': [handler_bad, handler_ok]}
        bus.publish('evt', 'x')
        # handler_bad 抛异常但不应阻止 handler_ok 执行
        handler_ok.assert_called_once_with('x')


class TestRedisEventBusSubscribe:
    """subscribe 方法"""

    def test_subscribe_new_event(self):
        from core.redis_event_bus import RedisEventBus
        bus = RedisEventBus()
        bus._redis = None
        handler = lambda d: None
        bus.subscribe('my_event', handler)
        assert handler in bus._subscribers['my_event']

    def test_subscribe_existing_event(self):
        from core.redis_event_bus import RedisEventBus
        bus = RedisEventBus()
        bus._redis = None
        h1 = lambda d: None
        h2 = lambda d: None
        bus.subscribe('evt', h1)
        bus.subscribe('evt', h2)
        assert len(bus._subscribers['evt']) == 2

    def test_subscribe_starts_listener(self):
        """订阅时如果 Redis 已连接且 listener 未启动，则启动"""
        from core.redis_event_bus import RedisEventBus
        mock_redis = MagicMock()
        bus = RedisEventBus()
        bus._redis = mock_redis
        bus._running = False
        with patch.object(bus, '_start_listener') as mock_start:
            bus.subscribe('evt', lambda d: None)
            mock_start.assert_called_once()

    def test_subscribe_no_listener_if_redis_none(self):
        from core.redis_event_bus import RedisEventBus
        bus = RedisEventBus()
        bus._redis = None
        with patch.object(bus, '_start_listener') as mock_start:
            bus.subscribe('evt', lambda d: None)
            mock_start.assert_not_called()

    def test_subscribe_does_not_restart_listener(self):
        from core.redis_event_bus import RedisEventBus
        mock_redis = MagicMock()
        bus = RedisEventBus()
        bus._redis = mock_redis
        bus._running = True
        with patch.object(bus, '_start_listener') as mock_start:
            bus.subscribe('evt', lambda d: None)
            mock_start.assert_not_called()


class TestRedisEventBusStartListener:
    """_start_listener 内部方法"""

    def test_start_listener_creates_thread(self):
        from core.redis_event_bus import RedisEventBus
        mock_redis = MagicMock()
        bus = RedisEventBus()
        bus._redis = mock_redis
        with patch('core.redis_event_bus.threading.Thread') as mock_thread:
            bus._start_listener()
            assert bus._running
            mock_thread.assert_called_once()
            mock_thread.return_value.start.assert_called_once()

    def test_listener_processes_message(self):
        """listener 收到消息后分发给订阅者"""
        from core.redis_event_bus import RedisEventBus
        mock_redis = MagicMock()
        # 模拟 pubsub.listen() 返回一个 message 然后停止
        msg = {'type': 'message', 'data': json.dumps({'event': 'order.updated', 'data': 'ok'})}
        mock_pubsub = MagicMock()
        mock_pubsub.listen.return_value = [msg]
        mock_redis.pubsub.return_value = mock_pubsub

        bus = RedisEventBus()
        bus._redis = mock_redis
        handler = MagicMock()
        bus._subscribers = {'order.updated': [handler]}

        bus._start_listener()
        import time
        time.sleep(0.1)

        # handler 应该被调用了
        handler.assert_called_with('ok')

    def test_listener_skips_non_message(self):
        from core.redis_event_bus import RedisEventBus
        mock_redis = MagicMock()
        msgs = [
            {'type': 'subscribe', 'data': 1},
            {'type': 'message', 'data': json.dumps({'event': 'e', 'data': 'd'})},
        ]
        mock_pubsub = MagicMock()
        mock_pubsub.listen.return_value = msgs
        mock_redis.pubsub.return_value = mock_pubsub

        bus = RedisEventBus()
        bus._redis = mock_redis
        handler = MagicMock()
        bus._subscribers = {'e': [handler]}
        bus._start_listener()
        import time
        time.sleep(0.1)
        handler.assert_called_once_with('d')

    def test_listener_bad_json(self):
        from core.redis_event_bus import RedisEventBus
        mock_redis = MagicMock()
        msg = {'type': 'message', 'data': 'not-json{{'}
        mock_pubsub = MagicMock()
        mock_pubsub.listen.return_value = [msg]
        mock_redis.pubsub.return_value = mock_pubsub

        bus = RedisEventBus()
        bus._redis = mock_redis
        bus._start_listener()
        import time
        time.sleep(0.1)
        # 不应报错

    def test_listener_handler_raises(self):
        from core.redis_event_bus import RedisEventBus
        mock_redis = MagicMock()
        msg = {'type': 'message', 'data': json.dumps({'event': 'boom', 'data': 'x'})}
        mock_pubsub = MagicMock()
        mock_pubsub.listen.return_value = [msg]
        mock_redis.pubsub.return_value = mock_pubsub

        bus = RedisEventBus()
        bus._redis = mock_redis
        handler = MagicMock(side_effect=ValueError("handler error"))
        bus._subscribers = {'boom': [handler]}
        bus._start_listener()
        import time
        time.sleep(0.1)
        handler.assert_called_once()

    def test_publish_both_redis_and_memory(self):
        """发布时同时走 Redis 和本地订阅"""
        from core.redis_event_bus import RedisEventBus
        mock_redis = MagicMock()
        bus = RedisEventBus()
        bus._redis = mock_redis
        handler = MagicMock()
        bus._subscribers = {'evt': [handler]}
        bus.publish('evt', 'data')
        # Redis publish
        mock_redis.publish.assert_called_once()
        # 本地 handler
        handler.assert_called_once_with('data')
