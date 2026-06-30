# -*- coding: utf-8 -*-
"""
Redis 客户端兼容层

当 real-redis 包不可用时，提供一个 stub 实现，
让依赖 redis.Redis 的代码可以优雅降级。
"""
import logging

logger = logging.getLogger(__name__)


class Redis:
    def __init__(self, host='localhost', port=6379, db=0, password=None,
                 socket_connect_timeout=2, socket_timeout=None, **kwargs):
        self._host = host
        self._port = port
        self._connected = False
        try:
            import redis as _real_redis
            self._client = _real_redis.Redis(
                host=host, port=port, db=db, password=password,
                socket_connect_timeout=socket_connect_timeout,
                socket_timeout=socket_timeout, **kwargs)
            self._client.ping()
            self._connected = True
        except Exception as e:
            logger.warning(f"[RedisStub] 连接失败: {e}，将使用内存降级")
            self._client = None
            raise ConnectionError(f"Redis 连接失败: {e}")

    def ping(self):
        if self._client:
            return self._client.ping()
        raise ConnectionError("Redis 未连接")

    def publish(self, channel, message):
        if self._client:
            return self._client.publish(channel, message)
        return 0

    def pubsub(self):
        if self._client:
            return self._client.pubsub()
        # StubPubSub 已在同文件内定义，直接使用
        return StubPubSub()

    def get(self, key):
        if self._client:
            return self._client.get(key)
        return None

    def set(self, key, value, ex=None):
        if self._client:
            return self._client.set(key, value, ex=ex)
        return True

    def delete(self, *keys):
        if self._client:
            return self._client.delete(*keys)
        return 0


class StubPubSub:
    def __init__(self):
        self._subs = {}

    def subscribe(self, **kwargs):
        for channel in kwargs:
            self._subs[channel] = True

    def unsubscribe(self, *channels):
        for channel in channels:
            self._subs.pop(channel, None)

    def get_message(self, timeout=0.1, ignore_subscribe_messages=True):
        return None

    def close(self):
        self._subs.clear()
