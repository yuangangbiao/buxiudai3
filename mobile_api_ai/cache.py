# -*- coding: utf-8 -*-
"""
Redis缓存层 - 分布式缓存

提供Redis缓存支持：
- 替代内存缓存，实现多实例共享
- Session存储
- 消息队列
- 分布式锁

使用方式：
    from cache import cache, redis_client

    # 缓存数据（10秒）
    cache.set('key', data, ttl=10)

    # 获取缓存
    data = cache.get('key')

    # 删除缓存
    cache.delete('key')

    # 分布式锁
    with DistributedLock('task_123'):
        # 临界区代码
        ...
"""
import os
import json
import time
import logging
from typing import Any, Optional, Callable
from contextlib import contextmanager

logger = logging.getLogger(__name__)

_redis_client = None


def _get_redis_config():
    """获取Redis配置"""
    return {
        'host': os.getenv('REDIS_HOST', 'localhost'),
        'port': int(os.getenv('REDIS_PORT', 6379)),
        'db': int(os.getenv('REDIS_DB', 0)),
        'password': os.getenv('REDIS_PASSWORD') or None,
        'decode_responses': True,
        'socket_timeout': 5,
        'socket_connect_timeout': 5,
    }


class RedisCache:
    """Redis缓存封装"""

    def __init__(self, client):
        self.client = client

    def get(self, key: str, default: Any = None) -> Any:
        """获取缓存值"""
        try:
            value = self.client.get(key)
            if value is None:
                return default
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except Exception as e:
            logger.warning(f"[Redis] GET {key} 失败: {e}")
            return default

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        try:
            if isinstance(value, (dict, list, tuple)):
                value = json.dumps(value, ensure_ascii=False)
            if ttl:
                self.client.setex(key, ttl, value)
            else:
                self.client.set(key, value)
            return True
        except Exception as e:
            logger.warning(f"[Redis] SET {key} 失败: {e}")
            return False

    def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"[Redis] DELETE {key} 失败: {e}")
            return False

    def exists(self, key: str) -> bool:
        """检查key是否存在"""
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            logger.warning(f"[Redis] EXISTS {key} 失败: {e}")
            return False

    def expire(self, key: str, ttl: int) -> bool:
        """设置过期时间"""
        try:
            return bool(self.client.expire(key, ttl))
        except Exception as e:
            logger.warning(f"[Redis] EXPIRE {key} 失败: {e}")
            return False

    def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """递增计数器"""
        try:
            return self.client.incrby(key, amount)
        except Exception as e:
            logger.warning(f"[Redis] INCR {key} 失败: {e}")
            return None

    def get_many(self, *keys: str) -> dict:
        """批量获取"""
        result = {}
        for key in keys:
            value = self.get(key)
            if value is not None:
                result[key] = value
        return result

    def set_many(self, mapping: dict, ttl: Optional[int] = None) -> bool:
        """批量设置"""
        pipe = self.client.pipeline()
        for key, value in mapping.items():
            if isinstance(value, (dict, list, tuple)):
                value = json.dumps(value, ensure_ascii=False)
            if ttl:
                pipe.setex(key, ttl, value)
            else:
                pipe.set(key, value)
        try:
            pipe.execute()
            return True
        except Exception as e:
            logger.warning(f"[Redis] MSET 失败: {e}")
            return False

    def clear_pattern(self, pattern: str) -> int:
        """清除匹配模式的所有key"""
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"[Redis] CLEAR {pattern} 失败: {e}")
            return 0


class DistributedLock:
    """分布式锁"""

    def __init__(self, name: str, timeout: int = 10, blocking: bool = True):
        self.name = f"lock:{name}"
        self.timeout = timeout
        self.blocking = blocking
        self.token = str(time.time()) + str(id(self))
        self._acquired = False

    def acquire(self) -> bool:
        """获取锁"""
        if not redis_client:
            logger.warning("[Redis] Redis未连接，分布式锁无效")
            return True

        try:
            if self.blocking:
                start = time.time()
                while time.time() - start < self.timeout:
                    if redis_client.client.set(self.name, self.token, nx=True, ex=self.timeout):
                        self._acquired = True
                        return True
                    time.sleep(0.01)
                return False
            else:
                if redis_client.client.set(self.name, self.token, nx=True, ex=self.timeout):
                    self._acquired = True
                    return True
                return False
        except Exception as e:
            logger.warning(f"[Redis] 获取锁 {self.name} 失败: {e}")
            return True

    def release(self) -> bool:
        """释放锁"""
        if not redis_client or not self._acquired:
            return True

        try:
            script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            result = redis_client.client.eval(script, 1, self.name, self.token)
            self._acquired = False
            return bool(result)
        except Exception as e:
            logger.warning(f"[Redis] 释放锁 {self.name} 失败: {e}")
            return False

    def __enter__(self):
        if not self.acquire():
            raise TimeoutError(f"获取锁 {self.name} 超时")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False


class RateLimiter:
    """基于Redis的请求限流器"""

    def __init__(self, key: str, max_requests: int, window: int):
        self.key = f"ratelimit:{key}"
        self.max_requests = max_requests
        self.window = window

    def is_allowed(self) -> bool:
        """检查是否允许请求"""
        if not redis_client:
            return True

        try:
            current = redis_client.client.get(self.key)
            if current is None:
                redis_client.client.setex(self.key, self.window, 1)
                return True

            if int(current) >= self.max_requests:
                return False

            redis_client.client.incr(self.key)
            return True
        except Exception as e:
            logger.warning(f"[Redis] RateLimit {self.key} 失败: {e}")
            return True


def _init_redis():
    """初始化Redis连接"""
    global _redis_client, redis_client

    try:
        import redis
        config = _get_redis_config()
        client = redis.Redis(**config)
        try:
            client.ping()
        except Exception:
            pass  # 首次 ping 失败不阻塞，后续操作会异常降级
        _redis_client = RedisCache(client)
        redis_client = _redis_client
        logger.info(f"[Redis] 连接成功: {config['host']}:{config['port']}")
        return _redis_client
    except ImportError:
        logger.warning("[Redis] redis模块未安装，缓存将使用内存后备")
        return None
    except Exception as e:
        logger.warning(f"[Redis] 连接失败: {e}，缓存将使用内存后备")
        return None


class _LazyCacheProxy:
    """惰性缓存代理 - 首次调用方法时才连接 Redis"""

    def _get_real_cache(self):
        try:
            c = _init_redis()
            return c or fallback_cache()
        except Exception:
            return fallback_cache()

    def __getattr__(self, name):
        c = self._get_real_cache()
        return getattr(c, name)

    def __bool__(self):
        return True


cache = _LazyCacheProxy()
redis_client = cache


def get_cache() -> Optional[RedisCache]:
    """获取缓存实例"""
    return cache


def fallback_cache():
    """内存后备缓存（当Redis不可用时）"""
    _memory_cache = {}

    class MemoryCache:
        def get(self, key, default=None):
            item = _memory_cache.get(key)
            if item is None:
                return default
            if item['expire'] and time.time() > item['expire']:
                del _memory_cache[key]
                return default
            return item['value']

        def set(self, key, value, ttl=None):
            expire = time.time() + ttl if ttl else None
            _memory_cache[key] = {'value': value, 'expire': expire}
            return True

        def delete(self, key):
            _memory_cache.pop(key, None)
            return True

    return MemoryCache()


if cache is None:
    cache = fallback_cache()
    redis_client = cache
    logger.info("[Cache] 使用内存后备缓存")
