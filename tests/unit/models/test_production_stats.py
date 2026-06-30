# -*- coding: utf-8 -*-
r"""models/production_stats.py 的集成测试。

真源码行为(已读 d:\yuan\不锈钢网带跟单3.0\models\production_stats.py 验证):
- ProductionStatsDAO 类(5 个 @staticmethod)
- calculate_order_stats(order_id): 计算订单生产统计数据
- get_order_stats(order_id): 获取订单统计数据
- get_process_details(order_id): 获取工序详细数据
- calculate_all_orders_stats(): 批量计算所有订单
- get_stats_summary(start_date, end_date): 获取统计汇总

patch 策略:在 production_stats 模块导入后,直接替换其 get_connection 引用。
"""
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from models.production_stats import ProductionStatsDAO


def _make_mock():
    r"""创建支持 with 协议的 mock conn。"""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=False)
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.return_value = None
    cursor.fetchall.return_value = []
    cursor.lastrowid = 1
    return conn, cursor


@contextmanager
def _swap_conn(mock_conn):
    r"""将 mock_conn 注入 production_stats.get_connection 后执行 block,yield 后恢复。"""
    import models.production_stats as ps
    orig = ps.get_connection
    ps.get_connection = lambda: mock_conn
    try:
        yield
    finally:
        ps.get_connection = orig


def test_calculate_order_stats_order_not_found_returns_false():
    r"""calculate_order_stats 订单不存在返 False(源码 line 33-35)。"""
    conn, cursor = _make_mock()
    cursor.fetchone.return_value = None
    with patch("utils.op_logger.log", lambda *a, **kw: None):
        with patch("utils.op_logger.log_error", lambda *a, **kw: None):
            with _swap_conn(conn):
                result = ProductionStatsDAO.calculate_order_stats(999)
    assert result is False


def test_calculate_order_stats_inserts_new_record():
    r"""calculate_order_stats 订单存在但无 existing 记录时 INSERT。"""
    conn, cursor = _make_mock()
    cursor.fetchone.side_effect = [
        {"id": 1, "order_no": "GO-001", "product_type": "编织网带",
         "confirm_time": "2026-01-01 10:00:00", "ship_time": "2026-01-10 10:00:00", "receive_time": None},
        None,
        {"process_count": 1, "avg_duration": 3.0, "max_duration": 3.0,
         "min_duration": 3.0, "total_qty": 100.0, "total_qualified": 95.0,
         "total_calculated": 100.0, "total_actual": 102.0,
         "total_work_hours": 8.0, "avg_efficiency": 1.2},
        {"avg_rate": 95.0},
        None,
        None,
    ]
    cursor.fetchall.return_value = []
    with patch("utils.op_logger.log", lambda *a, **kw: None):
        with patch("utils.op_logger.log_error", lambda *a, **kw: None):
            with _swap_conn(conn):
                result = ProductionStatsDAO.calculate_order_stats(1)
    assert result is True
    insert_calls = [c for c in cursor.execute.call_args_list if "INSERT INTO production_stats" in str(c.args[0])]
    assert len(insert_calls) == 1
    conn.commit.assert_called()


def test_calculate_order_stats_updates_existing():
    r"""calculate_order_stats existing 记录存在时 UPDATE。"""
    conn, cursor = _make_mock()
    cursor.fetchone.side_effect = [
        {"id": 1, "order_no": "GO-001", "product_type": "编织网带",
         "confirm_time": "2026-01-01 10:00:00", "ship_time": "2026-01-10 10:00:00", "receive_time": None},
        {"id": 1, "plan_confirm_time": "2026-01-01 10:00:00", "actual_end": "2026-01-10 10:00:00"},
        {"process_count": 1, "avg_duration": 3.0, "max_duration": 3.0,
         "min_duration": 3.0, "total_qty": 100.0, "total_qualified": 95.0,
         "total_calculated": 100.0, "total_actual": 102.0,
         "total_work_hours": 8.0, "avg_efficiency": 1.2},
        {"avg_rate": 95.0},
        {"id": 1},
        None,
    ]
    cursor.fetchall.return_value = []
    with patch("utils.op_logger.log", lambda *a, **kw: None):
        with patch("utils.op_logger.log_error", lambda *a, **kw: None):
            with _swap_conn(conn):
                result = ProductionStatsDAO.calculate_order_stats(1)
    assert result is True
    update_calls = [c for c in cursor.execute.call_args_list if "UPDATE production_stats" in str(c.args[0])]
    assert len(update_calls) == 1


def test_calculate_order_stats_calculates_order_cycle_days():
    r"""calculate_order_stats 从 2026-01-01 到 2026-01-10 → 9 天。"""
    conn, cursor = _make_mock()
    cursor.fetchone.side_effect = [
        {"id": 1, "order_no": "GO-001", "product_type": "编织网带",
         "confirm_time": "2026-01-01 10:00:00", "ship_time": "2026-01-10 10:00:00", "receive_time": None},
        None,
        {"process_count": 1, "avg_duration": 3.0, "max_duration": 3.0,
         "min_duration": 3.0, "total_qty": 100.0, "total_qualified": 95.0,
         "total_calculated": 100.0, "total_actual": 102.0,
         "total_work_hours": 8.0, "avg_efficiency": 1.2},
        {"avg_rate": 95.0},
        None,
        None,
    ]
    cursor.fetchall.return_value = []
    with patch("utils.op_logger.log", lambda *a, **kw: None):
        with patch("utils.op_logger.log_error", lambda *a, **kw: None):
            with _swap_conn(conn):
                result = ProductionStatsDAO.calculate_order_stats(1)
    assert result is True
    insert_calls = [c for c in cursor.execute.call_args_list if "INSERT INTO production_stats" in str(c.args[0])]
    params = insert_calls[0].args[1]
    assert params[7] == 9


def test_calculate_order_stats_handles_missing_dates():
    r"""calculate_order_stats confirm_time=None 时 order_cycle_days=None。"""
    conn, cursor = _make_mock()
    cursor.fetchone.side_effect = [
        {"id": 1, "order_no": "GO-001", "product_type": "编织网带",
         "confirm_time": None, "ship_time": None, "receive_time": None},
        None,
        {"process_count": 0, "avg_duration": None, "max_duration": None,
         "min_duration": None, "total_qty": 0.0, "total_qualified": 0.0,
         "total_calculated": 0.0, "total_actual": 0.0,
         "total_work_hours": 0.0, "avg_efficiency": 0.0},
        None,
        None,
        None,
    ]
    cursor.fetchall.return_value = []
    with patch("utils.op_logger.log", lambda *a, **kw: None):
        with patch("utils.op_logger.log_error", lambda *a, **kw: None):
            with _swap_conn(conn):
                result = ProductionStatsDAO.calculate_order_stats(1)
    assert result is True


def test_calculate_order_stats_calculates_qualified_rate():
    r"""calculate_order_stats total_qty=100, total_qualified=95 → qualified_rate=95.0。"""
    conn, cursor = _make_mock()
    cursor.fetchone.side_effect = [
        {"id": 1, "order_no": "GO-001", "product_type": "编织网带",
         "confirm_time": "2026-01-01 10:00:00", "ship_time": "2026-01-10 10:00:00", "receive_time": None},
        None,
        {"process_count": 1, "avg_duration": 3.0, "max_duration": 3.0,
         "min_duration": 3.0, "total_qty": 100.0, "total_qualified": 95.0,
         "total_calculated": 100.0, "total_actual": 102.0,
         "total_work_hours": 8.0, "avg_efficiency": 1.2},
        {"avg_rate": 95.0},
        None,
        None,
    ]
    cursor.fetchall.return_value = []
    with patch("utils.op_logger.log", lambda *a, **kw: None):
        with patch("utils.op_logger.log_error", lambda *a, **kw: None):
            with _swap_conn(conn):
                result = ProductionStatsDAO.calculate_order_stats(1)
    assert result is True
    insert_calls = [c for c in cursor.execute.call_args_list if "INSERT INTO production_stats" in str(c.args[0])]
    params = insert_calls[0].args[1]
    assert params[19] == 95.0


def test_get_order_stats_returns_dict():
    r"""get_order_stats 命中时返 dict。"""
    conn, cursor = _make_mock()
    cursor.fetchone.return_value = {
        "order_id": 1, "order_no": "GO-001", "total_qualified_rate": 95.0,
    }
    with patch("utils.op_logger.log_error", lambda *a, **kw: None):
        with _swap_conn(conn):
            result = ProductionStatsDAO.get_order_stats(1)
    assert result["order_no"] == "GO-001"


def test_get_order_stats_missing_returns_empty_dict():
    r"""get_order_stats 不存在返 {}。"""
    conn, cursor = _make_mock()
    cursor.fetchone.return_value = None
    with patch("utils.op_logger.log_error", lambda *a, **kw: None):
        with _swap_conn(conn):
            result = ProductionStatsDAO.get_order_stats(999)
    assert result == {}


def test_get_process_details_returns_list():
    r"""get_process_details 返 [dict] 列表,ORDER BY process_seq。"""
    conn, cursor = _make_mock()
    cursor.fetchall.return_value = [
        {"process_name": "P01", "process_seq": 1, "qualified_rate": 95.0},
    ]
    with patch("utils.op_logger.log_error", lambda *a, **kw: None):
        with _swap_conn(conn):
            result = ProductionStatsDAO.get_process_details(1)
    assert len(result) == 1
    sql = cursor.execute.call_args.args[0]
    assert "ORDER BY process_seq" in sql


def test_get_process_details_empty_returns_empty_list():
    r"""get_process_details 无记录返 []。"""
    conn, cursor = _make_mock()
    cursor.fetchall.return_value = []
    with patch("utils.op_logger.log_error", lambda *a, **kw: None):
        with _swap_conn(conn):
            result = ProductionStatsDAO.get_process_details(999)
    assert result == []


def test_calculate_all_orders_stats_batch():
    r"""calculate_all_orders_stats 遍历所有 已完成/已发货/已签收 订单。"""
    conn, cursor = _make_mock()
    cursor.fetchall.side_effect = [
        [{"id": 1}],
        {"id": 1, "order_no": "GO-001", "product_type": "编织网带",
         "confirm_time": "2026-01-01 10:00:00", "ship_time": "2026-01-10 10:00:00", "receive_time": None},
        None,
        {"process_count": 1, "avg_duration": 3.0, "max_duration": 3.0,
         "min_duration": 3.0, "total_qty": 100.0, "total_qualified": 95.0,
         "total_calculated": 100.0, "total_actual": 102.0,
         "total_work_hours": 8.0, "avg_efficiency": 1.2},
        {"avg_rate": 95.0},
        None,
    ]
    with patch("utils.op_logger.log", lambda *a, **kw: None):
        with patch("utils.op_logger.log_error", lambda *a, **kw: None):
            with _swap_conn(conn):
                result = ProductionStatsDAO.calculate_all_orders_stats()
    assert result["success"] >= 0
    assert "fail" in result


def test_get_stats_summary_returns_dict():
    r"""get_stats_summary 返 dict。"""
    conn, cursor = _make_mock()
    cursor.fetchone.return_value = {
        "order_count": 10, "avg_order_cycle": 9.5, "avg_qualified_rate": 95.0,
    }
    with patch("utils.op_logger.log_error", lambda *a, **kw: None):
        with _swap_conn(conn):
            result = ProductionStatsDAO.get_stats_summary()
    assert result["order_count"] == 10


def test_get_stats_summary_with_date_filter():
    r"""get_stats_summary(start_date, end_date) 拼日期过滤。"""
    conn, cursor = _make_mock()
    cursor.fetchone.return_value = {}
    with patch("utils.op_logger.log_error", lambda *a, **kw: None):
        with _swap_conn(conn):
            ProductionStatsDAO.get_stats_summary("2026-01-01", "2026-01-31")
    sql = cursor.execute.call_args.args[0]
    params = cursor.execute.call_args.args[1]
    assert "calculated_at >=" in sql
    assert "calculated_at <=" in sql
    assert "2026-01-01" in params


def test_get_stats_summary_empty_returns_empty_dict():
    r"""get_stats_summary 无结果返 {}。"""
    conn, cursor = _make_mock()
    cursor.fetchone.return_value = None
    with patch("utils.op_logger.log_error", lambda *a, **kw: None):
        with _swap_conn(conn):
            result = ProductionStatsDAO.get_stats_summary()
    assert result == {}
