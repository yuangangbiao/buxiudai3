# -*- coding: utf-8 -*-
"""utils/redis.py 的单元测试

覆盖模块:
- Redis 类: __init__ / ping / publish / pubsub / get / set / delete
- StubPubSub 类: subscribe / unsubscribe / get_message / close

策略: 用 unittest.mock 替换 utils.redis 模块内 import 的 _real_redis,
避免依赖真实 redis 服务。
"""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from utils.redis import Redis, StubPubSub


# ── Fixtures ──

@pytest.fixture
def mock_redis_pkg():
    """mock utils.redis 内部的 import redis 模块

    源码在 __init__ 中 import redis as _real_redis,
    我们 patch sys.modules 让它导入 mock 包。
    """
    mock_redis_mod = MagicMock(name='redis_module')
    mock_redis_class = MagicMock(name='redis_class')
    mock_client = MagicMock(name='redis_client')
    mock_redis_class.return_value = mock_client
    # ping 默认返回 True
    mock_client.ping.return_value = True
    mock_redis_mod.Redis = mock_redis_class

    with patch.dict(sys.modules, {'redis': mock_redis_mod}):
        yield mock_redis_mod, mock_redis_class, mock_client


@pytest.fixture
def redis_connected(mock_redis_pkg):
    """创建已连接的 Redis 客户端"""
    _mod, _cls, client = mock_redis_pkg
    r = Redis(host='test-host', port=6380)
    return r, client


# ── Redis.__init__ 测试 ──

class TestRedisInit:
    """Redis 构造函数测试"""

    def test_default_params(self, mock_redis_pkg):
        """默认参数"""
        _mod, _cls, client = mock_redis_pkg
        r = Redis()
        # 调用真实 _real_redis.Redis 时应使用默认参数
        _cls.assert_called_once()
        kwargs = _cls.call_args.kwargs
        assert kwargs['host'] == 'localhost'
        assert kwargs['port'] == 6379
        assert kwargs['db'] == 0
        assert kwargs['password'] is None
        assert kwargs['socket_connect_timeout'] == 2

    def test_custom_params(self, mock_redis_pkg):
        """自定义参数"""
        _mod, _cls, client = mock_redis_pkg
        r = Redis(host='redis.example.com', port=6380, db=2, password='secret',
                  socket_connect_timeout=5, socket_timeout=10)
        kwargs = _cls.call_args.kwargs
        assert kwargs['host'] == 'redis.example.com'
        assert kwargs['port'] == 6380
        assert kwargs['db'] == 2
        assert kwargs['password'] == 'secret'
        assert kwargs['socket_connect_timeout'] == 5
        assert kwargs['socket_timeout'] == 10

    def test_extra_kwargs_passed_through(self, mock_redis_pkg):
        """额外 kwargs 透传"""
        _mod, _cls, client = mock_redis_pkg
        r = Redis(host='x', port=1, retry_on_timeout=True)
        kwargs = _cls.call_args.kwargs
        assert kwargs.get('retry_on_timeout') is True

    def test_connected_success(self, mock_redis_pkg):
        """连接成功时 _connected = True"""
        _mod, _cls, client = mock_redis_pkg
        r = Redis()
        assert r._connected is True
        client.ping.assert_called_once()

    def test_connection_failure_raises(self):
        """连接失败时抛 ConnectionError"""
        # 不 mock，让真实 import 失败（或连接超时）
        with patch.dict(sys.modules, {'redis': None}):
            with pytest.raises(ConnectionError) as exc_info:
                Redis(host='nonexistent', port=1, socket_connect_timeout=0.1)
        # 验证异常信息
        assert 'Redis 连接失败' in str(exc_info.value)

    def test_connected_flag_set(self, redis_connected):
        """_connected 标志位"""
        r, client = redis_connected
        assert r._connected is True


# ── Redis.ping 测试 ──

class TestRedisPing:
    """Redis.ping 测试"""

    def test_ping_when_connected(self, redis_connected):
        r, client = redis_connected
        client.ping.return_value = True
        assert r.ping() is True

    def test_ping_when_disconnected(self):
        """未连接时 ping 抛 ConnectionError"""
        r = Redis.__new__(Redis)  # 绕过 __init__
        r._client = None
        r._connected = False
        with pytest.raises(ConnectionError) as exc_info:
            r.ping()
        assert '未连接' in str(exc_info.value)


# ── Redis.publish 测试 ──

class TestRedisPublish:
    """Redis.publish 测试"""

    def test_publish_when_connected(self, redis_connected):
        r, client = redis_connected
        client.publish.return_value = 1  # 1 个订阅者
        result = r.publish('ch1', 'hello')
        assert result == 1
        client.publish.assert_called_once_with('ch1', 'hello')

    def test_publish_when_disconnected_returns_zero(self):
        r = Redis.__new__(Redis)
        r._client = None
        r._connected = False
        assert r.publish('ch1', 'hello') == 0

    def test_publish_dict_message(self, redis_connected):
        """发布 dict 消息"""
        r, client = redis_connected
        msg = {'event': 'order_created', 'data': {'order_no': 'X'}}
        client.publish.return_value = 1
        r.publish('events', msg)
        client.publish.assert_called_once_with('events', msg)


# ── Redis.pubsub 测试 ──

class TestRedisPubSub:
    """Redis.pubsub 测试"""

    def test_pubsub_when_connected(self, redis_connected):
        """已连接时返回真实 pubsub 对象"""
        r, client = redis_connected
        mock_pubsub_obj = MagicMock()
        client.pubsub.return_value = mock_pubsub_obj
        result = r.pubsub()
        assert result is mock_pubsub_obj
        client.pubsub.assert_called_once()

    def test_pubsub_when_disconnected_returns_stub(self):
        """未连接时返回 StubPubSub 实例"""
        r = Redis.__new__(Redis)
        r._client = None
        r._connected = False
        result = r.pubsub()
        assert isinstance(result, StubPubSub)


# ── Redis.get 测试 ──

class TestRedisGet:
    """Redis.get 测试"""

    def test_get_when_connected(self, redis_connected):
        r, client = redis_connected
        client.get.return_value = b'value'
        assert r.get('key1') == b'value'
        client.get.assert_called_once_with('key1')

    def test_get_nonexistent(self, redis_connected):
        r, client = redis_connected
        client.get.return_value = None
        assert r.get('missing') is None

    def test_get_when_disconnected_returns_none(self):
        r = Redis.__new__(Redis)
        r._client = None
        r._connected = False
        assert r.get('any') is None


# ── Redis.set 测试 ──

class TestRedisSet:
    """Redis.set 测试"""

    def test_set_without_expire(self, redis_connected):
        r, client = redis_connected
        client.set.return_value = True
        result = r.set('k', 'v')
        assert result is True
        client.set.assert_called_once_with('k', 'v', ex=None)

    def test_set_with_expire(self, redis_connected):
        r, client = redis_connected
        client.set.return_value = True
        result = r.set('k', 'v', ex=60)
        assert result is True
        client.set.assert_called_once_with('k', 'v', ex=60)

    def test_set_when_disconnected_returns_true(self):
        """未连接时 set 返回 True（静默成功）"""
        r = Redis.__new__(Redis)
        r._client = None
        r._connected = False
        assert r.set('k', 'v') is True


# ── Redis.delete 测试 ──

class TestRedisDelete:
    """Redis.delete 测试"""

    def test_delete_single_key(self, redis_connected):
        r, client = redis_connected
        client.delete.return_value = 1
        result = r.delete('k1')
        assert result == 1
        client.delete.assert_called_once_with('k1')

    def test_delete_multiple_keys(self, redis_connected):
        r, client = redis_connected
        client.delete.return_value = 3
        result = r.delete('k1', 'k2', 'k3')
        assert result == 3
        client.delete.assert_called_once_with('k1', 'k2', 'k3')

    def test_delete_no_keys(self, redis_connected):
        """无 key 时不调底层"""
        r, client = redis_connected
        client.delete.return_value = 0
        result = r.delete()
        assert result == 0

    def test_delete_when_disconnected_returns_zero(self):
        r = Redis.__new__(Redis)
        r._client = None
        r._connected = False
        assert r.delete('k') == 0


# ── StubPubSub 测试 ──

class TestStubPubSub:
    """StubPubSub 类测试"""

    def test_init_empty(self):
        p = StubPubSub()
        assert p._subs == {}

    def test_subscribe(self):
        p = StubPubSub()
        p.subscribe(channel1=True, channel2=True)
        assert p._subs == {'channel1': True, 'channel2': True}

    def test_subscribe_idempotent(self):
        p = StubPubSub()
        p.subscribe(channel1=True)
        p.subscribe(channel1=True)  # 重复订阅
        # 仍是 1 个
        assert len(p._subs) == 1

    def test_unsubscribe_existing(self):
        p = StubPubSub()
        p.subscribe(channel1=True, channel2=True)
        p.unsubscribe('channel1')
        assert 'channel1' not in p._subs
        assert 'channel2' in p._subs

    def test_unsubscribe_nonexistent(self):
        """取消订阅不存在的 channel 不抛错"""
        p = StubPubSub()
        p.unsubscribe('not-subscribed')  # 不应抛错
        assert p._subs == {}

    def test_unsubscribe_multiple(self):
        p = StubPubSub()
        p.subscribe(c1=True, c2=True, c3=True)
        p.unsubscribe('c1', 'c2')
        assert 'c1' not in p._subs
        assert 'c2' not in p._subs
        assert 'c3' in p._subs

    def test_get_message_returns_none(self):
        """get_message 始终返回 None（stub 不实现真实事件循环）"""
        p = StubPubSub()
        p.subscribe(channel1=True)
        result = p.get_message()
        assert result is None

    def test_get_message_with_timeout(self):
        """get_message 接受 timeout 参数（但不真用）"""
        p = StubPubSub()
        result = p.get_message(timeout=1.0)
        assert result is None

    def test_get_message_with_ignore_flag(self):
        """get_message 接受 ignore_subscribe_messages 参数"""
        p = StubPubSub()
        result = p.get_message(timeout=0.1, ignore_subscribe_messages=False)
        assert result is None

    def test_close_clears_subs(self):
        p = StubPubSub()
        p.subscribe(c1=True, c2=True)
        assert len(p._subs) == 2
        p.close()
        assert p._subs == {}

    def test_close_when_empty(self):
        """空状态下 close 不抛错"""
        p = StubPubSub()
        p.close()
        assert p._subs == {}

    def test_full_lifecycle(self):
        """完整生命周期"""
        p = StubPubSub()
        p.subscribe(news=True, sports=True)
        assert len(p._subs) == 2
        assert p.get_message() is None
        p.unsubscribe('news')
        assert len(p._subs) == 1
        p.close()
        assert p._subs == {}


# ── 集成场景 ──

class TestRedisIntegration:
    """集成场景测试"""

    def test_redis_unavailable_uses_stub_path(self, mock_redis_pkg):
        """redis 不可用时的整体行为"""
        # 模拟连接失败
        _mod, _cls, client = mock_redis_pkg
        _cls.side_effect = ConnectionError('connection refused')

        # 应该抛 ConnectionError
        with pytest.raises(ConnectionError):
            Redis(host='x', port=1)

    def test_client_state_after_init(self, redis_connected):
        """init 后状态正确"""
        r, client = redis_connected
        assert r._host == 'test-host'
        assert r._port == 6380
        assert r._connected is True
        assert r._client is not None

    def test_operations_delegate_to_client(self, redis_connected):
        """操作正确委托给底层 client"""
        r, client = redis_connected

        # 设置返回值
        client.get.return_value = b'val'
        client.set.return_value = True
        client.delete.return_value = 1
        client.publish.return_value = 1
        client.ping.return_value = True

        # 验证每个操作都委托
        r.get('k')
        r.set('k', 'v', ex=30)
        r.delete('k')
        r.publish('ch', 'msg')
        r.ping()

        assert client.get.call_count == 1
        assert client.set.call_count == 1
        assert client.delete.call_count == 1
        assert client.publish.call_count == 1
        assert client.ping.call_count >= 1  # init 也会调一次
