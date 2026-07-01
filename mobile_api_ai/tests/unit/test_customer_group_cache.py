# -*- coding: utf-8 -*-
"""
[F6 P9 2026-06-10] customer_group 进程内缓存单元测试
覆盖:
1. 首次查询 → 跨 DB → 缓存命中
2. 二次查询 → 0 跨 DB (缓存命中)
3. 5 分钟过期 → 重新跨 DB
4. 钢带库挂 → 返回空字符串, 不写缓存 (下次还能重试)
5. invalidate 精准失效
6. invalidate 全量失效
7. 空 order_no 短路
8. 缓存值标准化 (strip / None)
"""
import time
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def clear_cache():
    """每个测试前后清空缓存, 防污染"""
    from dispatch_center._core import DispatchContext
    from dispatch_center._core import invalidate_customer_group_cache
    invalidate_customer_group_cache()
    yield
    invalidate_customer_group_cache()


class TestCustomerGroupCache:
    """customer_group 进程内缓存测试"""

    def test_first_query_hits_db_then_caches(self):
        """首次查询跨 DB 一次, 之后缓存命中"""
        from dispatch_center._core import (
            _get_customer_group_for_order,
            DispatchContext,
        )

        with patch('dispatch_center._core.get_steelbelt_cursor') as mock_cursor:
            mock_cursor.return_value = (
                MagicMock(),
                MagicMock(fetchone=MagicMock(return_value={'customer_group': ' VIP '}))
            )
            result = _get_customer_group_for_order('ORD-001')
            assert result == 'VIP'  # strip 后
            assert mock_cursor.call_count == 1

            # 二次查询应 0 次跨 DB
            result2 = _get_customer_group_for_order('ORD-001')
            assert result2 == 'VIP'
            assert mock_cursor.call_count == 1  # 关键: 未增加

    def test_cache_expires_after_ttl(self):
        """缓存 5 分钟后过期, 重新跨 DB"""
        from dispatch_center._core import (
            _get_customer_group_for_order,
            invalidate_customer_group_cache,
            DispatchContext,
        )

        with patch('dispatch_center._core.get_steelbelt_cursor') as mock_cursor:
            mock_cursor.return_value = (
                MagicMock(),
                MagicMock(fetchone=MagicMock(return_value={'customer_group': 'A'}))
            )
            _get_customer_group_for_order('ORD-002')
            assert mock_cursor.call_count == 1

            # 直接改缓存条目 time 到 5 分钟前, 模拟过期
            cache = DispatchContext.get_instance().customer_group_cache
            cache['ORD-002']['time'] = time.time() - 301
            _get_customer_group_for_order('ORD-002')
            assert mock_cursor.call_count == 2  # 缓存失效, 重新查 DB

        invalidate_customer_group_cache('ORD-002')

    def test_db_failure_returns_empty_without_caching(self):
        """钢带库挂 → 返回空字符串, 不写缓存 (下次还能重试)"""
        from dispatch_center._core import (
            _get_customer_group_for_order,
            DispatchContext,
        )

        with patch('dispatch_center._core.get_steelbelt_cursor') as mock_cursor:
            mock_cursor.side_effect = Exception('钢带库连接失败')

            # 第 1 次: 失败 → 返回空
            result1 = _get_customer_group_for_order('ORD-003')
            assert result1 == ''
            assert mock_cursor.call_count == 1

            # 第 2 次: 缓存应为空, 再次尝试 DB
            result2 = _get_customer_group_for_order('ORD-003')
            assert result2 == ''
            assert mock_cursor.call_count == 2  # 关键: 重试了

    def test_invalidate_specific_order(self):
        """invalidate 精准失效指定订单"""
        from dispatch_center._core import (
            _get_customer_group_for_order,
            invalidate_customer_group_cache,
        )

        with patch('dispatch_center._core.get_steelbelt_cursor') as mock_cursor:
            mock_cursor.return_value = (
                MagicMock(),
                MagicMock(fetchone=MagicMock(return_value={'customer_group': 'A'}))
            )
            _get_customer_group_for_order('ORD-A')
            _get_customer_group_for_order('ORD-B')
            assert mock_cursor.call_count == 2

            # 精准失效 ORD-A
            count = invalidate_customer_group_cache('ORD-A')
            assert count == 1

            # ORD-A 失效, ORD-B 仍在
            _get_customer_group_for_order('ORD-A')
            _get_customer_group_for_order('ORD-B')
            assert mock_cursor.call_count == 3  # ORD-A 重新查, ORD-B 命中

    def test_invalidate_all(self):
        """invalidate(None) 全量失效"""
        from dispatch_center._core import (
            _get_customer_group_for_order,
            invalidate_customer_group_cache,
        )

        with patch('dispatch_center._core.get_steelbelt_cursor') as mock_cursor:
            mock_cursor.return_value = (
                MagicMock(),
                MagicMock(fetchone=MagicMock(return_value={'customer_group': 'A'}))
            )
            _get_customer_group_for_order('ORD-1')
            _get_customer_group_for_order('ORD-2')
            assert mock_cursor.call_count == 2

            count = invalidate_customer_group_cache()
            assert count == 2

            # 全部失效 → 2 次新查询
            _get_customer_group_for_order('ORD-1')
            _get_customer_group_for_order('ORD-2')
            assert mock_cursor.call_count == 4

    def test_empty_order_no_short_circuit(self):
        """空 order_no 短路, 不查 DB 不写缓存"""
        from dispatch_center._core import _get_customer_group_for_order

        with patch('dispatch_center._core.get_steelbelt_cursor') as mock_cursor:
            assert _get_customer_group_for_order('') == ''
            assert _get_customer_group_for_order(None) == ''
            assert mock_cursor.call_count == 0

    def test_value_normalization(self):
        """缓存值标准化: strip + None → ''"""
        from dispatch_center._core import _get_customer_group_for_order

        # 含空白的 customer_group
        with patch('dispatch_center._core.get_steelbelt_cursor') as mock_cursor:
            mock_cursor.return_value = (
                MagicMock(),
                MagicMock(fetchone=MagicMock(return_value={'customer_group': '  VIP-A  '}))
            )
            assert _get_customer_group_for_order('ORD-X') == 'VIP-A'

        # None → ''
        with patch('dispatch_center._core.get_steelbelt_cursor') as mock_cursor:
            mock_cursor.return_value = (
                MagicMock(),
                MagicMock(fetchone=MagicMock(return_value={'customer_group': None}))
            )
            assert _get_customer_group_for_order('ORD-Y') == ''

        # row 为 None (订单不存在) → ''
        with patch('dispatch_center._core.get_steelbelt_cursor') as mock_cursor:
            mock_cursor.return_value = (
                MagicMock(),
                MagicMock(fetchone=MagicMock(return_value=None))
            )
            assert _get_customer_group_for_order('ORD-Z') == ''

    def test_cache_isolation_between_orders(self):
        """不同订单缓存独立"""
        from dispatch_center._core import _get_customer_group_for_order

        responses = iter([
            {'customer_group': 'A'},
            {'customer_group': 'B'},
            {'customer_group': 'C'},
        ])

        with patch('dispatch_center._core.get_steelbelt_cursor') as mock_cursor:
            mock_cursor.return_value = (
                MagicMock(),
                MagicMock(fetchone=MagicMock(side_effect=lambda: next(responses)))
            )
            assert _get_customer_group_for_order('O1') == 'A'
            assert _get_customer_group_for_order('O2') == 'B'
            assert _get_customer_group_for_order('O3') == 'C'
            assert mock_cursor.call_count == 3

            # 再次查询全部命中
            assert _get_customer_group_for_order('O1') == 'A'
            assert _get_customer_group_for_order('O2') == 'B'
            assert _get_customer_group_for_order('O3') == 'C'
            assert mock_cursor.call_count == 3  # 未增加
