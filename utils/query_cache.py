# -*- coding: utf-8 -*-
"""
查询缓存模块 - 减少重复数据库查询
"""

import os
import time
import hashlib
from typing import Any, Dict, Optional

# 缓存存储
_query_cache: Dict[str, dict] = {}

# 缓存配置
CACHE_TTL = 300  # 默认缓存有效期（秒）


def _get_max_cache_size() -> int:
    """获取最大缓存大小，优先从modular_config读取，fallback到环境变量"""
    try:
        from modular_config import ModularConfig
        _config = ModularConfig()
        return _config.get_config('cache.max_size', 100)
    except ImportError:
        return int(os.getenv('MAX_CACHE_SIZE', '100'))

MAX_CACHE_SIZE = _get_max_cache_size()


def _generate_cache_key(sql: str, params: tuple = ()) -> str:
    """生成查询缓存键"""
    key_str = f"{sql}:{params}"
    return hashlib.md5(key_str.encode()).hexdigest()


def get_cached_result(sql: str, params: tuple = ()) -> Optional[Any]:
    """获取缓存的查询结果"""
    key = _generate_cache_key(sql, params)
    if key in _query_cache:
        entry = _query_cache[key]
        if time.time() < entry['expire_at']:
            return entry['data']
        else:
            # 缓存过期，删除
            del _query_cache[key]
    return None


def set_cached_result(sql: str, params: tuple, data: Any, ttl: int = None):
    """设置查询结果缓存"""
    # 清理过期缓存
    _cleanup_expired_cache()
    
    # 如果缓存已满，删除最旧的
    if len(_query_cache) >= MAX_CACHE_SIZE:
        oldest_key = min(_query_cache.keys(), key=lambda k: _query_cache[k]['created_at'])
        del _query_cache[oldest_key]
    
    key = _generate_cache_key(sql, params)
    expire_time = time.time() + (ttl or CACHE_TTL)
    _query_cache[key] = {
        'data': data,
        'created_at': time.time(),
        'expire_at': expire_time
    }


def _cleanup_expired_cache():
    """清理所有过期的缓存"""
    now = time.time()
    expired_keys = [k for k, v in _query_cache.items() if v['expire_at'] <= now]
    for key in expired_keys:
        del _query_cache[key]


def clear_cache():
    """清空所有缓存"""
    _query_cache.clear()


def invalidate_cache(pattern: str = None):
    """根据模式失效缓存"""
    if pattern:
        keys_to_remove = [k for k in _query_cache.keys() if pattern in k]
        for key in keys_to_remove:
            del _query_cache[key]
    else:
        clear_cache()


def get_cache_stats() -> dict:
    """获取缓存统计信息"""
    _cleanup_expired_cache()
    return {
        'total_entries': len(_query_cache),
        'max_size': MAX_CACHE_SIZE,
        'ttl_seconds': CACHE_TTL
    }


# 数据变更时自动失效缓存的装饰器
def invalidate_on_update(table_name: str):
    """
    装饰器：当数据更新时自动失效相关表的缓存
    
    Usage:
        @invalidate_on_update('orders')
        def update_order(order_id, data):
            # 更新逻辑
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            # 失效与该表相关的缓存
            invalidate_cache(table_name)
            return result
        return wrapper
    return decorator