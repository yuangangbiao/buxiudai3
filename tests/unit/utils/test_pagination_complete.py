# -*- coding: utf-8 -*-
"""
utils/pagination.py 完整单元测试

覆盖模块:
- CacheItem
- MemoryCache
- Pager
- 工具函数
"""
import os
import sys
import pytest
from unittest.mock import Mock, MagicMock, patch
import time

class TestCacheItem:
    """CacheItem 单元测试"""

    def test_cache_item_init_with_ttl(self):
        """测试带TTL的缓存项初始化"""
        from utils.pagination import CacheItem

        item = CacheItem("test_value", ttl=10)

        assert item.value == "test_value"
        assert item.expires_at > time.time()

    def test_cache_item_init_without_ttl(self):
        """测试不带TTL的缓存项初始化"""
        from utils.pagination import CacheItem

        item = CacheItem("test_value", ttl=0)

        assert item.expires_at == float('inf')

    def test_cache_item_not_expired(self):
        """测试缓存项未过期"""
        from utils.pagination import CacheItem

        item = CacheItem("test_value", ttl=60)

        assert item.is_expired() is False

    def test_cache_item_expired(self):
        """测试缓存项已过期"""
        from utils.pagination import CacheItem

        item = CacheItem("test_value", ttl=0.001)
        time.sleep(0.01)

        assert item.is_expired() is True


class TestMemoryCache:
    """MemoryCache 单元测试"""

    def test_memory_cache_init(self):
        """测试内存缓存初始化"""
        from utils.pagination import MemoryCache

        cache = MemoryCache()

        assert cache._cache is not None
        assert isinstance(cache._cache, dict)

    def test_memory_cache_set_and_get(self):
        """测试设置和获取缓存"""
        from utils.pagination import MemoryCache

        cache = MemoryCache()
        cache.set("key1", "value1", ttl=60)

        result = cache.get("key1")

        assert result == "value1"

    def test_memory_cache_get_nonexistent(self):
        """测试获取不存在的缓存"""
        from utils.pagination import MemoryCache

        cache = MemoryCache()

        result = cache.get("nonexistent")

        assert result is None

    def test_memory_cache_delete(self):
        """测试删除缓存"""
        from utils.pagination import MemoryCache

        cache = MemoryCache()
        cache.set("key1", "value1")
        cache.delete("key1")

        result = cache.get("key1")

        assert result is None

    def test_memory_cache_clear(self):
        """测试清空缓存"""
        from utils.pagination import MemoryCache

        cache = MemoryCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()

        assert len(cache._cache) == 0

    def test_memory_cache_cleanup_expired(self):
        """测试清理过期缓存"""
        from utils.pagination import MemoryCache

        cache = MemoryCache()
        cache.set("key1", "value1", ttl=0.001)  # 即将过期
        cache.set("key2", "value2", ttl=60)
        time.sleep(0.01)

        count = cache.cleanup_expired()

        assert count == 1
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"


class TestPager:
    """Pager 单元测试"""

    def test_pager_init_default(self):
        """测试分页器默认初始化"""
        from utils.pagination import Pager

        pager = Pager(total=100)

        assert pager.total == 100
        assert pager.page == 1
        assert pager.page_size == 100

    def test_pager_init_custom(self):
        """测试分页器自定义初始化"""
        from utils.pagination import Pager

        pager = Pager(total=200, page=3, page_size=20)

        assert pager.total == 200
        assert pager.page == 3
        assert pager.page_size == 20

    def test_pager_offset(self):
        """测试偏移量计算"""
        from utils.pagination import Pager

        pager = Pager(total=100, page=3, page_size=20)

        assert pager.offset == 40

    def test_pager_offset_first_page(self):
        """测试第一页偏移量"""
        from utils.pagination import Pager

        pager = Pager(total=100, page=1, page_size=20)

        assert pager.offset == 0

    def test_pager_total_pages(self):
        """测试总页数"""
        from utils.pagination import Pager

        pager = Pager(total=105, page_size=20)

        assert pager.total_pages == 6

    def test_pager_total_pages_zero(self):
        """测试总页数为0"""
        from utils.pagination import Pager

        pager = Pager(total=0)

        assert pager.total_pages == 0

    def test_pager_has_next_true(self):
        """测试有下一页"""
        from utils.pagination import Pager

        pager = Pager(total=100, page=1, page_size=20)

        assert pager.has_next is True

    def test_pager_has_next_false(self):
        """测试没有下一页"""
        from utils.pagination import Pager

        pager = Pager(total=100, page=5, page_size=20)

        assert pager.has_next is False

    def test_pager_has_prev_true(self):
        """测试有上一页"""
        from utils.pagination import Pager

        pager = Pager(total=100, page=2, page_size=20)

        assert pager.has_prev is True

    def test_pager_has_prev_false(self):
        """测试没有上一页"""
        from utils.pagination import Pager

        pager = Pager(total=100, page=1, page_size=20)

        assert pager.has_prev is False

    def test_pager_to_dict(self):
        """测试转换为字典"""
        from utils.pagination import Pager

        pager = Pager(total=100, page=2, page_size=20)
        result = pager.to_dict()

        assert "total" in result
        assert "page" in result
        assert "page_size" in result
        assert "total_pages" in result
        assert "has_next" in result
        assert "has_prev" in result


class TestPagerEdgeCases:
    """Pager 边界情况测试"""

    def test_pager_page_below_minimum(self):
        """测试页码小于最小值"""
        from utils.pagination import Pager

        pager = Pager(total=100, page=0)

        assert pager.page == 1

    def test_pager_page_size_below_minimum(self):
        """测试每页大小小于最小值"""
        from utils.pagination import Pager

        pager = Pager(total=100, page_size=0)

        assert pager.page_size == 1

    def test_pager_page_size_above_maximum(self):
        """测试每页大小大于最大值"""
        from utils.pagination import Pager

        pager = Pager(total=100, page_size=2000)

        assert pager.page_size == 1000

    def test_pager_negative_total(self):
        """测试负数总数"""
        from utils.pagination import Pager

        pager = Pager(total=-10)

        assert pager.total == 0


class TestCacheUtilityFunctions:
    """缓存工具函数测试"""

    def test_get_cache_function_exists(self):
        """测试get_cache函数存在"""
        from utils.pagination import get_cache

        assert callable(get_cache)

    def test_set_cache_function_exists(self):
        """测试set_cache函数存在"""
        from utils.pagination import set_cache

        assert callable(set_cache)

    def test_invalidate_cache_function_exists(self):
        """测试invalidate_cache函数存在"""
        from utils.pagination import invalidate_cache

        assert callable(invalidate_cache)

    def test_clear_all_cache_function_exists(self):
        """测试clear_all_cache函数存在"""
        from utils.pagination import clear_all_cache

        assert callable(clear_all_cache)


class TestPagerConstants:
    """Pager 常量测试"""

    def test_default_page_size(self):
        """测试默认每页大小"""
        from utils.pagination import Pager

        assert Pager.DEFAULT_PAGE_SIZE == 100

    def test_max_page_size(self):
        """测试最大每页大小"""
        from utils.pagination import Pager

        assert Pager.MAX_PAGE_SIZE == 1000


class TestGlobalCacheInstance:
    """全局缓存实例测试"""

    def test_global_cache_exists(self):
        """测试全局缓存实例存在"""
        from utils.pagination import _cache

        assert _cache is not None

    def test_cached_decorator_exists(self):
        """测试cached装饰器存在"""
        from utils.pagination import cached

        assert callable(cached)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
