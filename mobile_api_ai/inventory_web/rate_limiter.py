# -*- coding: utf-8 -*-
"""库存管理 — 登录限流模块（TASK-017）

双后端：
- InMemoryRateLimiter: 内存后端（默认，单 worker 部署）
- RedisRateLimiter: Redis 后端（设置 REDIS_URL 自动启用，多 worker 部署）

配置：
- MAX_ATTEMPTS: 5 次
- LOCKOUT_SECONDS: 300 秒（5 分钟）
"""
import os
import secrets
import threading
import time
import logging
from abc import ABC, abstractmethod
from collections import defaultdict

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 300  # 5 分钟


class RateLimiterBase(ABC):
    """限流器抽象基类"""

    @abstractmethod
    def is_locked(self, key: str) -> bool:
        """检查 key 是否被锁定"""
        pass

    @abstractmethod
    def record_failure(self, key: str) -> int:
        """记录一次失败，返回当前失败次数"""
        pass

    @abstractmethod
    def record_success(self, key: str) -> None:
        """记录一次成功（清零失败计数）"""
        pass

    @abstractmethod
    def get_remaining_lock_seconds(self, key: str) -> int:
        """获取剩余锁定时间（秒）"""
        pass


class InMemoryRateLimiter(RateLimiterBase):
    """内存限流器（单 worker / 单进程部署）

    CRITICAL Fix H1/H4: 加 threading.Lock 保护 _attempts 字典，
    防止多线程下 list.append / 清理竞争导致计数丢失
    """

    def __init__(self):
        # {key: [failure_timestamp, ...]}
        self._attempts = defaultdict(list)
        # CRITICAL Fix H1: 线程安全锁
        self._lock = threading.Lock()

    def is_locked(self, key: str) -> bool:
        with self._lock:  # CRITICAL Fix H1: 加锁
            now = time.time()
            attempts = [t for t in self._attempts[key] if now - t < LOCKOUT_SECONDS]
            self._attempts[key] = attempts
            return len(attempts) >= MAX_ATTEMPTS

    def record_failure(self, key: str) -> int:
        with self._lock:  # CRITICAL Fix H1: 加锁
            now = time.time()
            # 先清理过期记录
            self._attempts[key] = [t for t in self._attempts[key] if now - t < LOCKOUT_SECONDS]
            self._attempts[key].append(now)
            return len(self._attempts[key])

    def record_success(self, key: str) -> None:
        with self._lock:  # CRITICAL Fix H1: 加锁
            self._attempts.pop(key, None)

    def get_remaining_lock_seconds(self, key: str) -> int:
        with self._lock:  # CRITICAL Fix H1: 加锁
            if not self._attempts.get(key):
                return 0
            now = time.time()
            latest = max(self._attempts[key])
            elapsed = now - latest
            remaining = LOCKOUT_SECONDS - elapsed
            return max(0, int(remaining))


class RedisRateLimiter(RateLimiterBase):
    """Redis 限流器（多 worker 部署）

    使用 sorted set 存储失败时间戳，原子操作避免竞争
    """

    def __init__(self, redis_url: str):
        try:
            import redis
            self._redis = redis.from_url(redis_url, decode_responses=True)
            # 测试连接
            self._redis.ping()
            logger.info(f'[限流] Redis 后端已连接: {redis_url}')
        except ImportError:
            logger.warning('[限流] redis 包未安装，回退到内存后端')
            self._fallback = InMemoryRateLimiter()
        except Exception as e:
            logger.warning(f'[限流] Redis 连接失败，回退到内存: {e}')
            self._fallback = InMemoryRateLimiter()

    def _key(self, key: str) -> str:
        return f'inv_login_fail:{key}'

    def is_locked(self, key: str) -> bool:
        if hasattr(self, '_fallback'):
            return self._fallback.is_locked(key)
        try:
            rkey = self._key(key)
            now = time.time()
            # 清理过期（ZREMRANGEBYSCORE）
            self._redis.zremrangebyscore(rkey, 0, now - LOCKOUT_SECONDS)
            # 当前计数
            count = self._redis.zcard(rkey)
            return count >= MAX_ATTEMPTS
        except Exception:
            # CRITICAL Fix H2: 失败时 fail-closed（锁定）
            # 原因：fail-open 会让 Redis 故障期间限流被绕过，
            #       攻击者可借此机会疯狂爆破
            logger.exception('[限流] Redis is_locked 失败，fail-closed 锁定')
            return True  # fail-closed

    def record_failure(self, key: str) -> int:
        if hasattr(self, '_fallback'):
            return self._fallback.record_failure(key)
        try:
            rkey = self._key(key)
            now = time.time()
            # CRITICAL Fix H3: member 用 "timestamp-random" 防同秒碰撞覆盖
            member = f'{now}-{secrets.token_hex(4)}'
            self._redis.zadd(rkey, {member: now})
            # 设置过期（避免冷数据）
            self._redis.expire(rkey, LOCKOUT_SECONDS + 60)
            # 返回当前计数
            return self._redis.zcard(rkey)
        except Exception:
            # CRITICAL Fix H2: fail-closed
            logger.exception('[限流] Redis record_failure 失败')
            return MAX_ATTEMPTS  # 视为已锁定

    def record_success(self, key: str) -> None:
        if hasattr(self, '_fallback'):
            return self._fallback.record_success(key)
        try:
            self._redis.delete(self._key(key))
        except Exception:
            logger.exception('[限流] Redis record_success 失败')

    def get_remaining_lock_seconds(self, key: str) -> int:
        if hasattr(self, '_fallback'):
            return self._fallback.get_remaining_lock_seconds(key)
        try:
            rkey = self._key(key)
            # 取最新时间戳
            latest_list = self._redis.zrange(rkey, -1, -1, withscores=True)
            if not latest_list:
                return 0
            latest_ts = latest_list[0][1]
            elapsed = time.time() - latest_ts
            return max(0, int(LOCKOUT_SECONDS - elapsed))
        except Exception:
            return LOCKOUT_SECONDS


def get_rate_limiter() -> RateLimiterBase:
    """工厂方法：按 REDIS_URL 环境变量自动选择后端"""
    redis_url = os.getenv('REDIS_URL')
    if redis_url:
        return RedisRateLimiter(redis_url)
    return InMemoryRateLimiter()


# 模块级单例（惰性初始化）
_limiter = None


def rate_limiter() -> RateLimiterBase:
    global _limiter
    if _limiter is None:
        _limiter = get_rate_limiter()
    return _limiter


# 修复 500 错误（CRITICAL）：
#   inventory_api_server.py:270 写的是
#     `from inventory_web.rate_limiter import rate_limiter as _login_limiter`
#   import 拿到的是函数对象本身（不是 limiter 实例），调用 .is_locked() 时抛
#   AttributeError: 'function' object has no attribute 'is_locked'
#   而 inventory_api_server.py 是已归档文件，不能直接修改。
#   在模块加载时把 `rate_limiter` 重新绑定为实例，
#   这样后续 `from rate_limiter import rate_limiter` 拿到的是 RateLimiterBase 实例。
# 命名上原本的工厂函数重命名为 _factory_rate_limiter（避免冲突）。
_factory_rate_limiter = rate_limiter  # 保留原函数名以防外部调用
rate_limiter = _factory_rate_limiter()  # 立即执行，得到实例并重绑定到模块名


# CRITICAL Fix L1: 测试用重置（仅测试环境用，不影响生产）
def reset_for_testing():
    """清空限流器状态（仅用于单元测试）

    生产环境绝对不要调用！
    """
    global _limiter
    if _limiter is not None:
        if isinstance(_limiter, InMemoryRateLimiter):
            with _limiter._lock:
                _limiter._attempts.clear()
        elif isinstance(_limiter, RedisRateLimiter):
            if not hasattr(_limiter, '_fallback'):
                # 清空所有 inv_login_fail:* 的 key
                try:
                    for key in _limiter._redis.scan_iter('inv_login_fail:*'):
                        _limiter._redis.delete(key)
                except Exception:
                    logger.exception('[限流] reset_for_testing 失败')
    _limiter = None  # 强制下次重建
