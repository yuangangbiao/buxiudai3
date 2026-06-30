# -*- coding: utf-8 -*-
"""Redis Pub/Sub 跨进程事件总线"""
import json
import threading
import logging

logger = logging.getLogger(__name__)

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class RedisEventBus:
    """Redis Pub/Sub 事件总线，支持跨进程 + 内存降级"""

    def __init__(self, host='localhost', port=6379, db=0, channel='steelbelt:events'):
        self._host = host
        self._port = port
        self._db = db
        self._channel = channel
        self._redis = None
        self._subscribers = {}  # 内存降级
        self._listener_thread = None
        self._running = False

        if REDIS_AVAILABLE:
            try:
                self._redis = redis.Redis(host=host, port=port, db=db, socket_connect_timeout=2)
                self._redis.ping()
                logger.info(f"[EventBus] Redis 已连接: {host}:{port}")
            except Exception as e:
                logger.warning(f"[EventBus] Redis 不可用，降级为内存模式: {e}")
                self._redis = None

    def publish(self, event, data):
        payload = json.dumps({'event': event, 'data': data}, ensure_ascii=False, default=str)
        if self._redis:
            try:
                self._redis.publish(self._channel, payload)
            except Exception as e:
                logger.warning(f"[EventBus] Redis publish 失败，仅内存: {e}")
        # 内存降级
        if event in self._subscribers:
            for handler in self._subscribers[event]:
                try:
                    handler(data)
                except Exception as e:
                    logger.error(f"[EventBus] 处理器异常: {e}", exc_info=True)

    def subscribe(self, event, handler):
        if event not in self._subscribers:
            self._subscribers[event] = []
        self._subscribers[event].append(handler)
        if self._redis and not self._running:
            self._start_listener()

    def _start_listener(self):
        self._running = True
        pubsub = self._redis.pubsub()
        pubsub.subscribe(self._channel)

        def _listen():
            for msg in pubsub.listen():
                if msg['type'] == 'message':
                    try:
                        payload = json.loads(msg['data'])
                        evt, data = payload['event'], payload['data']
                        if evt in self._subscribers:
                            for h in self._subscribers[evt]:
                                try:
                                    h(data)
                                except Exception as e:
                                    logger.error(f"[EventBus] 处理器异常: {e}")
                    except Exception as e:
                        logger.error(f"[EventBus] 消息解析失败: {e}")

        t = threading.Thread(target=_listen, daemon=True)
        t.start()
