import os
import time
import logging
from typing import Any, Optional, Callable

from cache import get_cache as _get_base_cache

logger = logging.getLogger(__name__)

REDIS_PREFIX = os.getenv('REDIS_PREFIX', 'cc:')


class _MemoryFallback:
    def __init__(self):
        self._store = {}
        self._expiry = {}

    def get(self, key):
        lookup = f'{REDIS_PREFIX}{key}'
        if lookup in self._expiry:
            if time.time() > self._expiry[lookup]:
                self.delete(key)
                return None
        return self._store.get(lookup)

    def set(self, key, value, ex=None):
        lookup = f'{REDIS_PREFIX}{key}'
        self._store[lookup] = value
        if ex:
            self._expiry[lookup] = time.time() + ex
        elif lookup in self._expiry:
            del self._expiry[lookup]

    def delete(self, key):
        lookup = f'{REDIS_PREFIX}{key}'
        self._store.pop(lookup, None)
        self._expiry.pop(lookup, None)

    def exists(self, key):
        lookup = f'{REDIS_PREFIX}{key}'
        if lookup in self._expiry:
            if time.time() > self._expiry[lookup]:
                self.delete(key)
                return False
        return lookup in self._store


class RedisCache:
    def __init__(self):
        self._base = _get_base_cache()
        self._memory = _MemoryFallback()

    def get(self, key: str) -> Optional[Any]:
        val = self._base.get(f'{REDIS_PREFIX}{key}')
        if val is not None:
            return val
        return self._memory.get(key)

    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        result = self._base.set(f'{REDIS_PREFIX}{key}', value, ttl=ex)
        self._memory.set(key, value, ex=ex)
        return result

    def delete(self, key: str) -> bool:
        self._base.delete(f'{REDIS_PREFIX}{key}')
        self._memory.delete(key)
        return True

    def exists(self, key: str) -> bool:
        return self._base.exists(f'{REDIS_PREFIX}{key}') or self._memory.exists(key)

    def get_or_set(self, key: str, fn: Callable, ex: Optional[int] = None) -> Any:
        cached = self.get(key)
        if cached is not None:
            return cached
        value = fn()
        if value is not None:
            self.set(key, value, ex=ex)
        return value

    def clear(self):
        self._base.clear_pattern(f'{REDIS_PREFIX}*')
        self._memory = _MemoryFallback()


cache = RedisCache()
