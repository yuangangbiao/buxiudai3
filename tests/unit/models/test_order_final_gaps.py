# -*- coding: utf-8 -*-
"""
OrderDAO 最终缝隙补齐
覆盖剩余行：118 (update 的 delivery_date 空字符串), 181-182 (cursor.close 异常),
186-187 (conn.close 异常), 466 (_fetch_page count_row=None), 803 (extra 缺生产工艺)
"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock


def _make_order_row(status="待确认", order_no="PO-001"):
    """创建模拟订单行（支持 dict 和 tuple 两种格式）"""
    row = MagicMock()
    row.__getitem__.side_effect = lambda k: {"status": status, "order_no": order_no}.get(k) if isinstance(k, str) else [status, order_no][k]
    row.get.side_effect = lambda k, d=None: {"status": status, "order_no": order_no}.get(k, d)
    return row


def _patch_and_import_order(patchers, mock_conn):
    """patch models.database.get_connection 并返回 OrderDAO"""
    from unittest.mock import patch
    p = patch("models.order.get_connection", return_value=mock_conn)
    p.start()
    patchers.append(p)
    from models.order import OrderDAO
    return OrderDAO


# ═══════════════════════════════════════════════════════════
# 1. OrderDAO.update — delivery_date 空字符串 + finally close
# ═══════════════════════════════════════════════════════════

class TestUpdateDeliveryDate:
    """OrderDAO.update 的 delivery_date 空字符串分支（第117-118行）"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor
        self.mock_cursor.fetchone.return_value = {"status": "待确认", "order_no": "PO-001"}
        self._patchers = []
        yield
        for p in self._patchers:
            p.stop()

    def test_update_empty_delivery_date(self):
        """update 带空 delivery_date -> 转为 None"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        result = OrderDAO.update(1, {"delivery_date": ""})
        assert result is True
        # 验证传给 SQL 的参数中 delivery_date 为 None
        call_args = self.mock_cursor.execute.call_args_list
        update_call = [c for c in call_args if "UPDATE orders" in str(c)][0]
        assert update_call[0][1][15] is None  # 第16个参数是 delivery_date


# ═══════════════════════════════════════════════════════════
# 2. OrderDAO.update — finally 块中 cursor.close / conn.close 异常保护
# ═══════════════════════════════════════════════════════════

class TestUpdateFinallyCloseExceptions:
    """OrderDAO.update 的 finally close 异常保护（第181-182,186-187行）"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor
        # 模拟正常流程
        self.mock_cursor.fetchone.return_value = {"status": "待确认", "order_no": "PO-001"}
        self._patchers = []
        yield
        for p in self._patchers:
            p.stop()

    def test_cursor_close_raises_exception(self):
        """finally 块中 cursor.close() 抛出异常被保护（L181-182）"""
        # 源码中 cursor 被赋值三次（L104, L120, L155），最后赋值的是第三个 cursor
        # 需要走完 try 块正常流程才会进入 finally
        # 让 finally 中的 cursor.close()（第4次调用）抛出异常
        self.mock_cursor.close.side_effect = [None, None, None, Exception("close failed")]
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        result = OrderDAO.update(1, {"customer_name": "测试"})
        assert result is True  # 异常被 finally 的 try/except pass 了

    def test_conn_close_raises_exception(self):
        """finally 块中 conn.close() 抛出异常被保护（L186-187）"""
        self.mock_cursor.close.side_effect = [None, None, None, None]
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        # conn.close() 在 finally 块内，必须走完 try 块正常流程才到那里
        self.mock_conn.close.side_effect = Exception("conn close boom")
        result = OrderDAO.update(1, {"customer_name": "测试"})
        assert result is True  # 异常被 finally 的 try/except pass 了


# ═══════════════════════════════════════════════════════════
# 3. _fetch_page — count_row 为 None（第466行）
# ═══════════════════════════════════════════════════════════

class TestFetchPageCountRowNone:
    """get_all_paginated 中 count_row 为 None -> total=0"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor
        # fetchone 返回 None → count_row is None → total = 0
        self.mock_cursor.fetchone.return_value = None
        self.mock_cursor.fetchall.return_value = []
        self._patchers = []
        yield
        for p in self._patchers:
            p.stop()

    def test_count_row_none(self):
        """count_row 为 None 时 total 为 0"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        result = OrderDAO.get_all_paginated()
        assert result["total"] == 0
        assert result["data"] == []
        assert result["has_next"] is False


# ═══════════════════════════════════════════════════════════
# 4. get_order_statistics — extra 缺"生产工艺"（第803行）
# ═══════════════════════════════════════════════════════════

class TestOrderDetailExtraMissing:
    """get_order_statistics 中 extra 不包含"生产工艺"时回退到 surface_treatment"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor
        self._patchers = []
        yield
        for p in self._patchers:
            p.stop()

    def test_extra_without_shengchan(self):
        """extra 不含 生产工艺 时使用 surface_treatment"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        # get_order_statistics 内部用 cursor.fetchone() 直接查数据库拿 order
        # 需要 mock 4 次 fetchone: L788(order), L810(confirmed_log), L817(completed_log), L832(production)
        self.mock_cursor.fetchone.side_effect = [
            {  # L788: 查询订单
                "id": 1, "order_no": "PO-001", "customer_name": "测试客户",
                "product_type": "网带", "material": "不锈钢",
                "width": 1.0, "length": 2.0, "quantity": 10, "unit": "米",
                "status": "待确认", "surface_treatment": "抛光处理",
                "extra_params": '{"备注": "无"}',  # 不含"生产工艺"
            },
            None,  # L810: confirmed_log
            None,  # L817: completed_log
            None,  # L832: production
        ]
        self.mock_cursor.fetchall.return_value = []
        result = OrderDAO.get_order_statistics(1)
        assert result["production_process"] == "抛光处理"
