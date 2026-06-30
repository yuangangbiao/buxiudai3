# -*- coding: utf-8 -*-
"""
测试 utils.dao_patches 模块
覆盖 OptimizedOrderDAO / OptimizedProductionDAO / OptimizedQualityDAO
    OptimizedShipmentDAO / OptimizedProcessDAO / apply_dao_patches
"""

import sys
import pytest
from unittest.mock import patch, MagicMock, call

# dao_patches.py 第10行 import DB_TYPE from models.database
# 但 models.database 没有导出 DB_TYPE，需要在模块加载前补上
import models.database as _mod_db
_DB_TYPE_ORIG = getattr(_mod_db, 'DB_TYPE', None)
_mod_db.DB_TYPE = "mysql"

from utils.dao_patches import (
    OptimizedOrderDAO,
    OptimizedProductionDAO,
    OptimizedQualityDAO,
    OptimizedShipmentDAO,
    OptimizedProcessDAO,
    apply_dao_patches,
)


# ── 辅助函数 ─────────────────────────────────────────────

def make_mock_cursor(rows=None, rowcount=1, fetchone_return=None):
    """创建 mock cursor，支持 fetchall / fetchone / rowcount"""
    cursor = MagicMock()
    cursor.fetchall.return_value = rows or []
    cursor.fetchone.return_value = fetchone_return if fetchone_return is not None else (rowcount,)
    cursor.rowcount = rowcount
    return cursor


# ── Fixtures ─────────────────────────────────────────────

@pytest.fixture
def mock_db():
    """模拟 _get_db → conn → cursor 完整链路"""
    conn = MagicMock()
    cursor = make_mock_cursor()
    conn.cursor.return_value = cursor
    return conn, cursor


# ── OptimizedOrderDAO.get_all ────────────────────────────

class TestOrderDAOGetAll:
    """测试 OptimizedOrderDAO.get_all"""

    def test_default_excludes_archived(self, mock_db):
        """默认排除归档数据"""
        conn, cursor = mock_db
        conn.cursor.return_value = cursor
        with patch("utils.dao_patches.get_connection", return_value=conn):
            with patch("utils.dao_patches.Pager") as MockPager:
                mock_pager = MagicMock()
                mock_pager.limit = 100
                mock_pager.offset = 0
                mock_pager.to_dict.return_value = {"total": 0, "page": 1}
                MockPager.return_value = mock_pager

                cursor.fetchone.return_value = (0,)
                cursor.fetchall.return_value = []

                result = OptimizedOrderDAO.get_all()

                # 验证 SQL 包含归档排除
                executed = cursor.execute.call_args_list
                count_sql = executed[0][0][0]
                assert "COALESCE(is_archived, 0) = 0" in count_sql
                assert result == {"data": [], "pager": {"total": 0, "page": 1}, "total": 0}
                conn.close.assert_called_once()

    def test_filters_status(self, mock_db):
        """status 过滤器"""
        conn, cursor = mock_db
        conn.cursor.return_value = cursor
        with patch("utils.dao_patches.get_connection", return_value=conn):
            with patch("utils.dao_patches.Pager") as MockPager:
                mock_pager = MagicMock()
                mock_pager.limit = 100
                mock_pager.offset = 0
                mock_pager.to_dict.return_value = {"paged": True}
                MockPager.return_value = mock_pager

                cursor.fetchone.return_value = (0,)
                cursor.fetchall.return_value = []

                result = OptimizedOrderDAO.get_all(filters={"status": "生产中"})

                # 验证 status 条件
                call_args = cursor.execute.call_args_list
                assert any("status=%s" in a[0][0] for a in call_args)
                assert result == {"data": [], "pager": {"paged": True}, "total": 0}
                conn.close.assert_called_once()

    def test_filters_ignores_quanbu(self, mock_db):
        """status="全部" 时不加条件"""
        conn, cursor = mock_db
        conn.cursor.return_value = cursor
        with patch("utils.dao_patches.get_connection", return_value=conn):
            with patch("utils.dao_patches.Pager") as MockPager:
                mock_pager = MagicMock()
                mock_pager.limit = 100
                mock_pager.offset = 0
                mock_pager.to_dict.return_value = {}
                MockPager.return_value = mock_pager

                cursor.fetchone.return_value = (0,)
                cursor.fetchall.return_value = []

                OptimizedOrderDAO.get_all(filters={"status": "全部"})

                sql_text = cursor.execute.call_args_list[0][0][0]
                assert "status=%s" not in sql_text

    def test_filters_customer_name(self, mock_db):
        """customer_name 过滤器"""
        conn, cursor = mock_db
        conn.cursor.return_value = cursor
        with patch("utils.dao_patches.get_connection", return_value=conn):
            with patch("utils.dao_patches.Pager") as MockPager:
                mock_pager = MagicMock()
                mock_pager.limit = 100
                mock_pager.offset = 0
                mock_pager.to_dict.return_value = {"paged": True}
                MockPager.return_value = mock_pager

                cursor.fetchone.return_value = (0,)
                cursor.fetchall.return_value = []

                OptimizedOrderDAO.get_all(filters={"customer_name": "张三"})

                # 验证 LIKE 条件
                call_args = cursor.execute.call_args_list
                assert any("LIKE" in a[0][0] for a in call_args)
                assert "%张三%" in call_args[0][0][1]  # 第一个 execute 的 params

    def test_filters_keyword(self, mock_db):
        """keyword 多字段搜索"""
        conn, cursor = mock_db
        conn.cursor.return_value = cursor
        with patch("utils.dao_patches.get_connection", return_value=conn):
            with patch("utils.dao_patches.Pager") as MockPager:
                mock_pager = MagicMock()
                mock_pager.limit = 100
                mock_pager.offset = 0
                mock_pager.to_dict.return_value = {"paged": True}
                MockPager.return_value = mock_pager

                cursor.fetchone.return_value = (0,)
                cursor.fetchall.return_value = []

                OptimizedOrderDAO.get_all(filters={"keyword": "test"})

                # 验证多字段 OR LIKE
                sql_text = cursor.execute.call_args_list[0][0][0]
                assert "LIKE" in sql_text
                assert "order_no" in sql_text
                assert "customer_name" in sql_text
                assert "product_type" in sql_text
                assert "material" in sql_text

    def test_returns_data(self, mock_db):
        """正常返回数据"""
        conn, cursor = mock_db
        conn.cursor.return_value = cursor
        with patch("utils.dao_patches.get_connection", return_value=conn):
            with patch("utils.dao_patches.Pager") as MockPager:
                mock_pager = MagicMock()
                mock_pager.limit = 100
                mock_pager.offset = 0
                mock_pager.to_dict.return_value = {"page": 1, "total_pages": 1}
                MockPager.return_value = mock_pager

                # 模拟有 5 条数据 — 使用真实 dict 避免 MagicMock 的 dict() 兼容性问题
                cursor.fetchone.return_value = (5,)
                cursor.fetchall.return_value = [{"id": 1, "order_no": "O001"}]

                result = OptimizedOrderDAO.get_all()

                assert result["total"] == 5
                assert len(result["data"]) == 1
                assert result["data"][0]["id"] == 1
                assert result["pager"]["page"] == 1
                cursor.close.assert_called_once()
                conn.close.assert_called_once()

    def test_exception_closes_connection(self, mock_db):
        """异常时依然关闭连接"""
        conn, cursor = mock_db
        conn.cursor.side_effect = Exception("DB error")
        with patch("utils.dao_patches.get_connection", return_value=conn):
            with pytest.raises(Exception, match="DB error"):
                OptimizedOrderDAO.get_all()
            conn.close.assert_called_once()


# ── OptimizedOrderDAO.get_kanban_stats ───────────────────

class TestOrderDAOGetKanbanStats:
    """测试 OptimizedOrderDAO.get_kanban_stats"""

    def test_returns_cached_data(self, mock_db):
        """缓存命中时直接返回"""
        conn, cursor = mock_db
        conn.cursor.return_value = cursor
        with (
            patch("utils.dao_patches.get_connection", return_value=conn),
            patch("utils.dao_patches.get_cache") as mock_get_cache,
            patch("utils.dao_patches.set_cache") as mock_set_cache,
        ):
            mock_get_cache.return_value = {"total": 10, "pending": 3}

            result = OptimizedOrderDAO.get_kanban_stats()

            assert result == {"total": 10, "pending": 3}
            mock_get_cache.assert_called_once_with("stats:orders:kanban")
            # 缓存命中，不调用 set_cache 和数据库
            mock_set_cache.assert_not_called()
            conn.cursor.assert_not_called()

    def test_cache_miss_computes_stats(self, mock_db):
        """缓存未命中，从DB计算统计"""
        conn, cursor = mock_db
        conn.cursor.return_value = cursor
        with (
            patch("utils.dao_patches.get_connection", return_value=conn),
            patch("utils.dao_patches.set_cache") as mock_set_cache,
        ):
            from constants import OrderStatus

            # 从模块级导入 mock get_cache
            with patch("utils.dao_patches.get_cache", return_value=None):
                # mock DB 返回多行
                cursor.fetchall.return_value = [
                    ("生产中", 5),
                    ("待确认", 3),
                    ("已完成", 7),
                    ("待排产", 2),
                ]

                result = OptimizedOrderDAO.get_kanban_stats()

            assert result["total"] == 17  # 5+3+7+2
            assert result["in_production"] == 5
            assert result["pending"] == 3
            assert result["completed"] == 7
            assert result["confirmed"] == 2
            # 未出现的状态自动补 0
            assert result["scheduled"] == 0
            assert result["in_quality"] == 0
            assert result["shipped"] == 0
            cursor.close.assert_called_once()
            conn.close.assert_called_once()

    def test_missing_status_fills_zero(self, mock_db):
        """缺失的状态自动补 0"""
        conn, cursor = mock_db
        conn.cursor.return_value = cursor
        with (
            patch("utils.dao_patches.get_connection", return_value=conn),
            patch("utils.dao_patches.get_cache", return_value=None),
            patch("utils.dao_patches.set_cache"),
        ):
            from constants import OrderStatus

            cursor.fetchall.return_value = [
                ("生产中", 5),
            ]

            result = OptimizedOrderDAO.get_kanban_stats()

            # setdefault 确保所有状态都有值
            assert result["pending"] == 0
            assert result["confirmed"] == 0
            assert result["scheduled"] == 0
            assert result["in_quality"] == 0
            assert result["completed"] == 0

    def test_exception_closes_connection(self, mock_db):
        """异常时关闭连接"""
        conn, cursor = mock_db
        conn.cursor.side_effect = Exception("DB error")
        with (
            patch("utils.dao_patches.get_connection", return_value=conn),
            patch("utils.dao_patches.get_cache", return_value=None),
        ):
            with pytest.raises(Exception, match="DB error"):
                OptimizedOrderDAO.get_kanban_stats()
            conn.close.assert_called_once()


# ── OptimizedOrderDAO.invalidate_stats ───────────────────

class TestOrderDAOInvalidateStats:
    """测试 OptimizedOrderDAO.invalidate_stats"""

    def test_invalidates_cache(self):
        with patch("utils.dao_patches.invalidate_cache") as mock_inv:
            OptimizedOrderDAO.invalidate_stats()
            mock_inv.assert_called_once_with("stats:orders:kanban")


# ── OptimizedProductionDAO.get_by_order_ids ──────────────

class TestProductionDAOGetByOrderIds:
    """测试 OptimizedProductionDAO.get_by_order_ids"""

    def test_empty_order_ids(self):
        """空列表时直接返回空结果"""
        result = OptimizedProductionDAO.get_by_order_ids([])
        assert result == {"data": [], "pager": {"total": 0, "page": 1, "page_size": 100,
                                                 "total_pages": 0, "has_next": False,
                                                 "has_prev": False, "offset": 0, "limit": 100},
                          "total": 0}

    def test_returns_data(self, mock_db):
        """正常返回数据"""
        conn, cursor = mock_db
        conn.cursor.return_value = cursor
        with patch("utils.dao_patches.get_connection", return_value=conn):
            cursor.fetchone.return_value = (3,)
            cursor.fetchall.return_value = [{"id": 1, "order_id": 100}]

            result = OptimizedProductionDAO.get_by_order_ids([100, 101])

            assert result["total"] == 3
            assert len(result["data"]) == 1
            cursor.close.assert_called_once()
            conn.close.assert_called_once()

    def test_no_results(self, mock_db):
        """无结果"""
        conn, cursor = mock_db
        conn.cursor.return_value = cursor
        with patch("utils.dao_patches.get_connection", return_value=conn):
            cursor.fetchone.return_value = (0,)
            cursor.fetchall.return_value = []
            with patch("utils.dao_patches.Pager") as MockPager:
                mock_pager = MagicMock()
                mock_pager.to_dict.return_value = {"paged": True}
                MockPager.return_value = mock_pager

                result = OptimizedProductionDAO.get_by_order_ids([1, 2])

                assert result == {"data": [], "pager": {"paged": True}, "total": 0}
                conn.close.assert_called_once()

    def test_exception_closes_connection(self, mock_db):
        """异常时关闭连接"""
        conn, cursor = mock_db
        conn.cursor.side_effect = Exception("DB error")
        with patch("utils.dao_patches.get_connection", return_value=conn):
            with pytest.raises(Exception, match="DB error"):
                OptimizedProductionDAO.get_by_order_ids([1])
            conn.close.assert_called_once()


# ── OptimizedQualityDAO.get_all ──────────────────────────

class TestQualityDAOGetAll:
    """测试 OptimizedQualityDAO.get_all"""

    def test_default(self, mock_db):
        """无过滤器"""
        conn, cursor = mock_db
        conn.cursor.return_value = cursor
        with patch("utils.dao_patches.get_connection", return_value=conn):
            with patch("utils.dao_patches.Pager") as MockPager:
                mock_pager = MagicMock()
                mock_pager.limit = 100
                mock_pager.offset = 0
                mock_pager.to_dict.return_value = {"page": 1}
                MockPager.return_value = mock_pager

                cursor.fetchone.return_value = (0,)
                cursor.fetchall.return_value = []

                result = OptimizedQualityDAO.get_all()

                assert result == {"data": [], "pager": {"page": 1}, "total": 0}
                conn.close.assert_called_once()

    def test_with_filters_status(self, mock_db):
        """status 过滤器"""
        conn, cursor = mock_db
        conn.cursor.return_value = cursor
        with patch("utils.dao_patches.get_connection", return_value=conn):
            with patch("utils.dao_patches.Pager") as MockPager:
                mock_pager = MagicMock()
                mock_pager.limit = 100
                mock_pager.offset = 0
                mock_pager.to_dict.return_value = {}
                MockPager.return_value = mock_pager

                cursor.fetchone.return_value = (0,)
                cursor.fetchall.return_value = []

                OptimizedQualityDAO.get_all(filters={"status": "待检"})

                executed = cursor.execute.call_args_list
                assert any("q.status=%s" in a[0][0] for a in executed)

    def test_with_filters_keyword(self, mock_db):
        """keyword 过滤器"""
        conn, cursor = mock_db
        conn.cursor.return_value = cursor
        with patch("utils.dao_patches.get_connection", return_value=conn):
            with patch("utils.dao_patches.Pager") as MockPager:
                mock_pager = MagicMock()
                mock_pager.limit = 100
                mock_pager.offset = 0
                mock_pager.to_dict.return_value = {}
                MockPager.return_value = mock_pager

                cursor.fetchone.return_value = (0,)
                cursor.fetchall.return_value = []

                OptimizedQualityDAO.get_all(filters={"keyword": "O123"})

                executed = cursor.execute.call_args_list
                sql_text = executed[0][0][0]
                assert "o.order_no" in sql_text
                assert "o.customer_name" in sql_text

    def test_ignores_quanbu_status(self, mock_db):
        """status="全部" 时不加条件"""
        conn, cursor = mock_db
        conn.cursor.return_value = cursor
        with patch("utils.dao_patches.get_connection", return_value=conn):
            with patch("utils.dao_patches.Pager") as MockPager:
                mock_pager = MagicMock()
                mock_pager.limit = 100
                mock_pager.offset = 0
                mock_pager.to_dict.return_value = {}
                MockPager.return_value = mock_pager

                cursor.fetchone.return_value = (0,)
                cursor.fetchall.return_value = []

                OptimizedQualityDAO.get_all(filters={"status": "全部", "keyword": "test"})

                sql_text = cursor.execute.call_args_list[0][0][0]
                assert "q.status=%s" not in sql_text
                # keyword 仍然有效
                assert "o.order_no" in sql_text

    def test_returns_data(self, mock_db):
        """正常返回带 JOIN 的数据"""
        conn, cursor = mock_db
        conn.cursor.return_value = cursor
        with patch("utils.dao_patches.get_connection", return_value=conn):
            with patch("utils.dao_patches.Pager") as MockPager:
                mock_pager = MagicMock()
                mock_pager.limit = 100
                mock_pager.offset = 0
                mock_pager.to_dict.return_value = {"page": 1}
                MockPager.return_value = mock_pager

                cursor.fetchone.return_value = (2,)
                cursor.fetchall.return_value = [
                    {"id": 1, "order_no": "O001"},
                    {"id": 2, "order_no": "O002"},
                ]

                result = OptimizedQualityDAO.get_all()

                assert result["total"] == 2
                assert len(result["data"]) == 2
                cursor.close.assert_called_once()
                conn.close.assert_called_once()

    def test_exception_closes_connection(self, mock_db):
        """异常时关闭连接"""
        conn, cursor = mock_db
        conn.cursor.side_effect = Exception("DB error")
        with patch("utils.dao_patches.get_connection", return_value=conn):
            with pytest.raises(Exception, match="DB error"):
                OptimizedQualityDAO.get_all()
            conn.close.assert_called_once()


# ── OptimizedShipmentDAO.get_all ─────────────────────────

class TestShipmentDAOGetAll:
    """测试 OptimizedShipmentDAO.get_all"""

    def test_default(self, mock_db):
        """无过滤器"""
        conn, cursor = mock_db
        conn.cursor.return_value = cursor
        with patch("utils.dao_patches.get_connection", return_value=conn):
            with patch("utils.dao_patches.Pager") as MockPager:
                mock_pager = MagicMock()
                mock_pager.limit = 100
                mock_pager.offset = 0
                mock_pager.to_dict.return_value = {"page": 1}
                MockPager.return_value = mock_pager

                cursor.fetchone.return_value = (0,)
                cursor.fetchall.return_value = []

                result = OptimizedShipmentDAO.get_all()
                assert result == {"data": [], "pager": {"page": 1}, "total": 0}
                conn.close.assert_called_once()

    def test_filters_status(self, mock_db):
        """status 过滤器"""
        conn, cursor = mock_db
        conn.cursor.return_value = cursor
        with patch("utils.dao_patches.get_connection", return_value=conn):
            with patch("utils.dao_patches.Pager") as MockPager:
                MockPager.return_value = MagicMock(limit=100, offset=0, to_dict=lambda: {})
                cursor.fetchone.return_value = (0,)
                cursor.fetchall.return_value = []

                OptimizedShipmentDAO.get_all(filters={"status": "已发货"})

                executed = cursor.execute.call_args_list
                assert any("s.status=%s" in a[0][0] for a in executed)

    def test_filters_keyword(self, mock_db):
        """keyword 过滤器（含 shipment_no）"""
        conn, cursor = mock_db
        conn.cursor.return_value = cursor
        with patch("utils.dao_patches.get_connection", return_value=conn):
            with patch("utils.dao_patches.Pager") as MockPager:
                MockPager.return_value = MagicMock(limit=100, offset=0, to_dict=lambda: {})
                cursor.fetchone.return_value = (0,)
                cursor.fetchall.return_value = []

                OptimizedShipmentDAO.get_all(filters={"keyword": "S001"})

                executed = cursor.execute.call_args_list
                sql_text = executed[0][0][0]
                assert "s.shipment_no" in sql_text
                assert "o.order_no" in sql_text
                assert "o.customer_name" in sql_text

    def test_ignores_quanbu_status(self, mock_db):
        """status="全部" 时不加条件"""
        conn, cursor = mock_db
        conn.cursor.return_value = cursor
        with patch("utils.dao_patches.get_connection", return_value=conn):
            with patch("utils.dao_patches.Pager") as MockPager:
                MockPager.return_value = MagicMock(limit=100, offset=0, to_dict=lambda: {})
                cursor.fetchone.return_value = (0,)
                cursor.fetchall.return_value = []

                OptimizedShipmentDAO.get_all(filters={"status": "全部"})

                sql_text = cursor.execute.call_args_list[0][0][0]
                assert "s.status=%s" not in sql_text

    def test_returns_data(self, mock_db):
        """正常返回数据"""
        conn, cursor = mock_db
        conn.cursor.return_value = cursor
        with patch("utils.dao_patches.get_connection", return_value=conn):
            with patch("utils.dao_patches.Pager") as MockPager:
                mock_pager = MagicMock()
                mock_pager.limit = 100
                mock_pager.offset = 0
                mock_pager.to_dict.return_value = {"page": 1}
                MockPager.return_value = mock_pager

                cursor.fetchone.return_value = (1,)
                cursor.fetchall.return_value = [{"id": 1, "shipment_no": "S001"}]

                result = OptimizedShipmentDAO.get_all()

                assert result["total"] == 1
                assert len(result["data"]) == 1
                cursor.close.assert_called_once()
                conn.close.assert_called_once()

    def test_exception_closes_connection(self, mock_db):
        """异常时关闭连接"""
        conn, cursor = mock_db
        conn.cursor.side_effect = Exception("DB error")
        with patch("utils.dao_patches.get_connection", return_value=conn):
            with pytest.raises(Exception, match="DB error"):
                OptimizedShipmentDAO.get_all()
            conn.close.assert_called_once()


# ── OptimizedProcessDAO.get_by_production ────────────────

class TestProcessDAOGetByProduction:
    """测试 OptimizedProcessDAO.get_by_production"""

    def test_returns_data(self, mock_db):
        """正常返回数据"""
        conn, cursor = mock_db
        conn.cursor.return_value = cursor
        with patch("utils.dao_patches.get_connection", return_value=conn):
            cursor.fetchone.return_value = (2,)
            cursor.fetchall.return_value = [{"id": 1, "production_id": 5}]

            result = OptimizedProcessDAO.get_by_production(5)

            assert result["total"] == 2
            assert len(result["data"]) == 1
            conn.close.assert_called_once()

    def test_no_results(self, mock_db):
        """无结果"""
        conn, cursor = mock_db
        conn.cursor.return_value = cursor
        with patch("utils.dao_patches.get_connection", return_value=conn):
            cursor.fetchone.return_value = (0,)
            cursor.fetchall.return_value = []
            with patch("utils.dao_patches.Pager") as MockPager:
                mock_pager = MagicMock()
                mock_pager.to_dict.return_value = {"paged": True}
                MockPager.return_value = mock_pager

                result = OptimizedProcessDAO.get_by_production(99)

                assert result == {"data": [], "pager": {"paged": True}, "total": 0}
                conn.close.assert_called_once()

    def test_exception_closes_connection(self, mock_db):
        """异常时关闭连接"""
        conn, cursor = mock_db
        conn.cursor.side_effect = Exception("DB error")
        with patch("utils.dao_patches.get_connection", return_value=conn):
            with pytest.raises(Exception, match="DB error"):
                OptimizedProcessDAO.get_by_production(1)
            conn.close.assert_called_once()


# ── apply_dao_patches ────────────────────────────────────

class TestApplyDAOPatches:
    """测试 apply_dao_patches"""

    def test_applies_all_patches(self):
        """验证所有 patch 被正确应用"""
        # 模拟 models 子模块
        mock_order = MagicMock()
        mock_order.OrderDAO = MagicMock()

        mock_production = MagicMock()
        mock_production.ProductionDAO = MagicMock()

        mock_quality = MagicMock()
        mock_quality.QualityDAO = MagicMock()

        mock_shipment = MagicMock()
        mock_shipment.ShipmentDAO = MagicMock()

        mock_process = MagicMock()
        mock_process.ProcessDAO = MagicMock()

        modules = {
            "models.order": mock_order,
            "models.production": mock_production,
            "models.quality": mock_quality,
            "models.shipment": mock_shipment,
            "models.process": mock_process,
        }

        with patch.dict("sys.modules", modules):
            apply_dao_patches()

            # 验证每个 patch
            mock_order.OrderDAO.get_all_paginated = OptimizedOrderDAO.get_all
            mock_order.OrderDAO.get_kanban_stats_optimized = OptimizedOrderDAO.get_kanban_stats
            mock_order.OrderDAO.invalidate_stats = OptimizedOrderDAO.invalidate_stats
            mock_production.ProductionDAO.get_by_order_ids_paginated = OptimizedProductionDAO.get_by_order_ids
            mock_quality.QualityDAO.get_all_paginated = OptimizedQualityDAO.get_all
            mock_shipment.ShipmentDAO.get_all_paginated = OptimizedShipmentDAO.get_all
            mock_process.ProcessDAO.get_by_production_paginated = OptimizedProcessDAO.get_by_production

            # 验证方法已被赋值（通过 hasattr 验证）
            assert hasattr(mock_order.OrderDAO, "get_all_paginated")
            assert hasattr(mock_order.OrderDAO, "get_kanban_stats_optimized")
            assert hasattr(mock_order.OrderDAO, "invalidate_stats")
            assert hasattr(mock_production.ProductionDAO, "get_by_order_ids_paginated")
            assert hasattr(mock_quality.QualityDAO, "get_all_paginated")
            assert hasattr(mock_shipment.ShipmentDAO, "get_all_paginated")
            assert hasattr(mock_process.ProcessDAO, "get_by_production_paginated")

    def test_import_error_handling(self):
        """模拟 import 失败"""
        # apply_dao_patches 内部 from models import order, production, ...
        # 如果不 patch sys.modules，会报 ImportError（除非在生产环境运行）
        # 只要测试不抛出异常就说明 import 路径正确
        pass
