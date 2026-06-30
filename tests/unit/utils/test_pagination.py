# -*- coding: utf-8 -*-
"""utils/pagination.py 单元测试"""
import time
import pytest
from unittest.mock import MagicMock, patch


# ============================================================
# CacheItem
# ============================================================
class TestCacheItem:
    def test_create_with_ttl(self):
        from utils.pagination import CacheItem
        item = CacheItem("hello", ttl=60)
        assert item.value == "hello"
        assert not item.is_expired()

    def test_expired_after_ttl(self):
        from utils.pagination import CacheItem
        item = CacheItem("hello", ttl=0.001)
        time.sleep(0.002)
        assert item.is_expired()

    def test_no_expiry_when_ttl_zero(self):
        from utils.pagination import CacheItem
        item = CacheItem("hello", ttl=0)
        assert not item.is_expired()


# ============================================================
# MemoryCache
# ============================================================
class TestMemoryCache:
    def test_set_and_get(self):
        from utils.pagination import MemoryCache
        cache = MemoryCache()
        cache.set("k", "v")
        assert cache.get("k") == "v"

    def test_get_missing_key_returns_none(self):
        from utils.pagination import MemoryCache
        cache = MemoryCache()
        assert cache.get("nonexistent") is None

    def test_get_expired_returns_none_and_deletes(self):
        from utils.pagination import MemoryCache
        cache = MemoryCache()
        cache.set("k", "v", ttl=0.001)
        time.sleep(0.002)
        assert cache.get("k") is None
        # key should be deleted after expired get
        assert cache.get("k") is None

    def test_delete(self):
        from utils.pagination import MemoryCache
        cache = MemoryCache()
        cache.set("k", "v")
        cache.delete("k")
        assert cache.get("k") is None

    def test_delete_nonexistent_no_error(self):
        from utils.pagination import MemoryCache
        cache = MemoryCache()
        cache.delete("nonexistent")  # should not raise

    def test_clear(self):
        from utils.pagination import MemoryCache
        cache = MemoryCache()
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_cleanup_expired(self):
        from utils.pagination import MemoryCache
        cache = MemoryCache()
        cache.set("a", 1, ttl=0.001)
        cache.set("b", 2, ttl=60)
        time.sleep(0.002)
        removed = cache.cleanup_expired()
        assert removed == 1
        assert cache.get("a") is None
        assert cache.get("b") == 2

    def test_cleanup_no_expired_returns_zero(self):
        from utils.pagination import MemoryCache
        cache = MemoryCache()
        cache.set("a", 1, ttl=60)
        cache.set("b", 2, ttl=60)
        assert cache.cleanup_expired() == 0


# ============================================================
# cached decorator
# ============================================================
class TestCachedDecorator:
    def test_first_call_executes(self):
        from utils.pagination import cached, clear_all_cache
        clear_all_cache()
        call_count = [0]

        @cached(ttl=60, key_prefix="test")
        def f(x):
            call_count[0] += 1
            return x * 2

        result = f(5)
        assert result == 10
        assert call_count[0] == 1

    def test_second_call_uses_cache(self):
        from utils.pagination import cached, clear_all_cache
        clear_all_cache()
        call_count = [0]

        @cached(ttl=60, key_prefix="test2")
        def f(x):
            call_count[0] += 1
            return x * 2

        assert f(5) == 10
        assert f(5) == 10
        assert call_count[0] == 1  # only called once

    def test_different_args_different_keys(self):
        from utils.pagination import cached, clear_all_cache
        clear_all_cache()
        call_count = [0]

        @cached(ttl=60, key_prefix="test3")
        def f(x):
            call_count[0] += 1
            return x * 2

        f(5)
        f(10)
        assert call_count[0] == 2  # different args, both called


# ============================================================
# Global cache functions
# ============================================================
class TestGlobalCache:
    def test_set_and_get_cache(self):
        from utils.pagination import set_cache, get_cache, clear_all_cache
        clear_all_cache()
        set_cache("g1", "vv", ttl=60)
        assert get_cache("g1") == "vv"

    def test_invalidate_cache(self):
        from utils.pagination import set_cache, get_cache, invalidate_cache, clear_all_cache
        clear_all_cache()
        set_cache("g2", "vv", ttl=60)
        invalidate_cache("g2")
        assert get_cache("g2") is None

    def test_clear_all_cache(self):
        from utils.pagination import set_cache, get_cache, clear_all_cache
        set_cache("a", 1)
        set_cache("b", 2)
        clear_all_cache()
        assert get_cache("a") is None
        assert get_cache("b") is None


# ============================================================
# Pager
# ============================================================
class TestPager:
    def test_basic_properties(self):
        from utils.pagination import Pager
        p = Pager(total=100, page=1, page_size=10)
        assert p.total == 100
        assert p.page == 1
        assert p.page_size == 10
        assert p.offset == 0
        assert p.limit == 10
        assert p.total_pages == 10

    def test_offset_page2(self):
        from utils.pagination import Pager
        p = Pager(total=100, page=3, page_size=10)
        assert p.offset == 20

    def test_total_zero(self):
        from utils.pagination import Pager
        p = Pager(total=0, page=1, page_size=10)
        assert p.total_pages == 0
        assert p.offset == 0
        assert p.has_next is False
        assert p.has_prev is False

    def test_negative_total_clamped(self):
        from utils.pagination import Pager
        p = Pager(total=-5, page=1)
        assert p.total == 0
        assert p.total_pages == 0

    def test_page_zero_clamped_to_one(self):
        from utils.pagination import Pager
        p = Pager(total=100, page=0)
        assert p.page == 1
        assert p.offset == 0

    def test_page_size_exceeds_max(self):
        from utils.pagination import Pager
        p = Pager(total=500, page=1, page_size=2000)
        assert p.page_size == 1000  # MAX_PAGE_SIZE
        assert p.total_pages == 1

    def test_page_size_zero_clamped_to_one(self):
        from utils.pagination import Pager
        p = Pager(total=100, page=1, page_size=0)
        assert p.page_size == 1
        assert p.total_pages == 100

    def test_has_next(self):
        from utils.pagination import Pager
        p = Pager(total=25, page=1, page_size=10)
        assert p.has_next is True

    def test_has_next_false_on_last_page(self):
        from utils.pagination import Pager
        p = Pager(total=25, page=3, page_size=10)
        assert p.total_pages == 3
        assert p.has_next is False

    def test_has_prev(self):
        from utils.pagination import Pager
        p = Pager(total=50, page=3, page_size=10)
        assert p.has_prev is True

    def test_has_prev_false_on_first_page(self):
        from utils.pagination import Pager
        p = Pager(total=50, page=1, page_size=10)
        assert p.has_prev is False

    def test_to_dict(self):
        from utils.pagination import Pager
        p = Pager(total=45, page=2, page_size=10)
        d = p.to_dict()
        assert d["total"] == 45
        assert d["page"] == 2
        assert d["page_size"] == 10
        assert d["total_pages"] == 5
        assert d["has_next"] is True
        assert d["has_prev"] is True
        assert d["offset"] == 10
        assert d["limit"] == 10

    def test_last_page_partial(self):
        from utils.pagination import Pager
        p = Pager(total=7, page=2, page_size=5)
        assert p.total_pages == 2
        assert p.has_next is False


# ============================================================
# paginate_query
# ============================================================
class TestPaginateQuery:
    def test_empty_result(self):
        from utils.pagination import paginate_query
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = [0]
        mock_cursor.fetchall.return_value = []

        r = paginate_query(
            "SELECT * FROM t LIMIT :limit OFFSET :offset",
            "SELECT COUNT(*) FROM t",
            mock_conn,
            page=1,
            page_size=10,
        )
        assert r["data"] == []
        assert r["total"] == 0
        assert r["pager"]["total_pages"] == 0

    def test_with_results(self):
        from utils.pagination import paginate_query
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = [50]

        class Row(dict):
            pass
        mock_cursor.fetchall.return_value = [{"id": 1}, {"id": 2}]

        r = paginate_query(
            "SELECT * FROM t LIMIT :limit OFFSET :offset",
            "SELECT COUNT(*) FROM t",
            mock_conn,
            page=2,
            page_size=5,
        )
        assert r["total"] == 50
        assert r["pager"]["page"] == 2
        assert r["pager"]["total_pages"] == 10
        assert len(r["data"]) == 2

    def test_cursor_closed_after_error(self):
        from utils.pagination import paginate_query
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = RuntimeError("db error")

        with pytest.raises(RuntimeError, match="db error"):
            paginate_query("SQL", "COUNT SQL", mock_conn)
        mock_cursor.close.assert_called_once()

    def test_params_passed(self):
        from utils.pagination import paginate_query
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = [1]
        mock_cursor.fetchall.return_value = [{"id": 1}]

        paginate_query(
            "SELECT * FROM t WHERE x=%s LIMIT :limit OFFSET :offset",
            "SELECT COUNT(*) FROM t WHERE x=%s",
            mock_conn,
            params=[42],
        )
        # count query with params
        mock_cursor.execute.assert_any_call("SELECT COUNT(*) FROM t WHERE x=%s", [42])


# ============================================================
# get_common_cache_keys
# ============================================================
class TestCommonCacheKeys:
    def test_returns_dict_with_keys(self):
        from utils.pagination import get_common_cache_keys
        keys = get_common_cache_keys()
        assert isinstance(keys, dict)
        assert "product_types" in keys
        assert "process_templates" in keys
        assert "material_densities" in keys
        assert "material_rules" in keys
        assert "order_stats" in keys
        assert "production_stats" in keys
