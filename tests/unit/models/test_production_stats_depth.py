# -*- coding: utf-8 -*-
"""
深度测试 ProductionStatsDAO — 目标 60%+ 覆盖率
"""
import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime


# ── 辅助函数 ──────────────────────────────────────────────

class Row(dict):
    """继承 dict 的可查询 mock 行，解决 MagicMock 的 dict() 陷阱"""
    pass


def _order_row(**overrides):
    row = Row(
        id=1, order_no="PO-20260601-001",
        product_type="冷冻网带",
        confirm_time="2026-06-01 08:00:00",
        ship_time="2026-06-10 18:00:00",
        receive_time="2026-06-15 10:00:00",
    )
    row.update(overrides)
    return row


def _production_row(**overrides):
    row = Row(
        id=1,
        plan_confirm_time="2026-06-02 08:00:00",
        actual_end="2026-06-09 17:00:00",
    )
    row.update(overrides)
    return row


def _process_stats_row(**overrides):
    row = Row(
        process_count=3,
        avg_duration=2.5,
        max_duration=5.0,
        min_duration=1.0,
        total_qty=100,
        total_qualified=95,
        total_calculated=120,
        total_actual=125,
        total_work_hours=48.0,
        avg_efficiency=0.95,
    )
    row.update(overrides)
    return row


def _process_empty_stats():
    return Row(
        process_count=0,
        avg_duration=None,
        max_duration=None,
        min_duration=None,
        total_qty=0,
        total_qualified=0,
        total_calculated=0,
        total_actual=0,
        total_work_hours=0,
        avg_efficiency=None,
    )


def _avg_rate_row(**overrides):
    row = Row(avg_rate=92.5)
    row.update(overrides)
    return row


def _make_cursor_and_conn():
    cursor = MagicMock()
    cursor.close.return_value = None
    conn = MagicMock()
    conn.cursor.return_value = cursor
    conn.close.return_value = None
    return cursor, conn


# ── Fixtures ───────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_deps():
    """
    全局 mock 所有外部依赖

    注意：production_stats.py 的 log/log_error 是自由变量（NameError）
    而非模块属性，不能用 patch(string) 方式 mock。
    改为直接注入 mock 到模块 __dict__ 并 patch get_connection。
    """
    class _Mocks:
        pass
    m = _Mocks()

    # 1. patch get_connection (正常 from-import 的模块属性)
    m.get_connection = patch("models.production_stats.get_connection").start()

    # 2. 直接注入 mock 到模块的全局命名空间
    m.log = MagicMock()
    m.log_error = MagicMock()
    import models.production_stats as _ps_module
    _ps_module.log = m.log
    _ps_module.log_error = m.log_error

    yield m

    patch.stopall()
    # 清理注入
    _ps_module.log = None
    _ps_module.log_error = None


@pytest.fixture
def conn(mock_deps):
    """获取 mock 连接 (get_connection 的 return_value)"""
    return mock_deps.get_connection.return_value


@pytest.fixture
def dao():
    from models.production_stats import ProductionStatsDAO
    return ProductionStatsDAO


# ═══════════════════════════════════════════════════════════
# calculate_order_stats
# ═══════════════════════════════════════════════════════════

class TestCalculateOrderStats:
    """ProductionStatsDAO.calculate_order_stats"""

    @staticmethod
    def _setup_cursor_fetchone(conn, returns):
        """
        创建单个 cursor，将其 fetchone.side_effect 设为 returns 列表。
        calculate_order_stats 只创建一次 cursor 并复用做多次 execute+fetchone。
        """
        cursor = MagicMock()
        cursor.close.return_value = None
        cursor.fetchone.side_effect = returns
        conn.cursor.return_value = cursor
        return cursor

    def test_calculate_insert_success(self, dao, conn):
        """正常计算 - INSERT 路径（无已有统计记录）"""
        order = _order_row()
        prod = _production_row()
        stats = _process_stats_row()
        rate = _avg_rate_row()

        cursor = self._setup_cursor_fetchone(conn, [
            order,       # 第1次 fetchone: 订单信息
            prod,        # 第2次: 生产订单
            stats,       # 第3次: 工序统计
            rate,        # 第4次: AVG 合格率
            None,        # 第5次: 无已有统计（INSERT 路径）
        ])

        result = dao.calculate_order_stats(1)

        assert result is True
        conn.commit.assert_called_once()
        conn.close.assert_called_once()

        # 验证 INSERT 调用（第 5 次 execute）
        execute_calls = cursor.execute.call_args_list
        last_sql = execute_calls[-1][0][0]
        assert "INSERT INTO production_stats" in last_sql

    def test_calculate_update_success(self, dao, conn):
        """正常计算 - UPDATE 路径（已有统计记录）"""
        order = _order_row()
        prod = _production_row()
        stats = _process_stats_row()
        rate = _avg_rate_row()

        cursor = self._setup_cursor_fetchone(conn, [
            order,          # 第1次: 订单
            prod,           # 第2次: 生产订单
            stats,          # 第3次: 工序统计
            rate,           # 第4次: AVG 合格率
            Row(id=1),      # 第5次: 已有统计（UPDATE）
        ])

        result = dao.calculate_order_stats(1)

        assert result is True
        conn.commit.assert_called_once()

        execute_calls = cursor.execute.call_args_list
        last_sql = execute_calls[-1][0][0]
        assert "UPDATE production_stats" in last_sql

    def test_calculate_order_not_found(self, dao, conn):
        """订单不存在时返回 False"""
        cursor, _ = _make_cursor_and_conn()
        cursor.fetchone.return_value = None
        conn.cursor.return_value = cursor

        result = dao.calculate_order_stats(999)

        assert result is False
        conn.commit.assert_not_called()
        conn.close.assert_called_once()

    def test_calculate_no_process_stats(self, dao, conn):
        """无工序记录（process_stats 全为 None/0)"""
        order = _order_row()
        prod = _production_row()

        cursor = self._setup_cursor_fetchone(conn, [
            order,
            prod,
            _process_empty_stats(),
            _avg_rate_row(avg_rate=None),
            None,
        ])

        result = dao.calculate_order_stats(1)

        assert result is True
        conn.commit.assert_called_once()

    def test_calculate_no_production_order(self, dao, conn):
        """无生产工单（production_id 等为 None）"""
        order = _order_row()
        stats = _process_stats_row()
        rate = _avg_rate_row()

        cursor = self._setup_cursor_fetchone(conn, [
            order,
            None,     # 无生产订单
            stats,
            rate,
            None,
        ])

        result = dao.calculate_order_stats(1)

        assert result is True
        conn.commit.assert_called_once()

    def test_calculate_no_times(self, dao, conn):
        """所有时间为 None（order_cycle、delivery、production 均为 None）"""
        order = _order_row(
            confirm_time=None,
            ship_time=None,
            receive_time=None,
        )
        prod = _production_row(
            plan_confirm_time=None,
            actual_end=None,
        )
        stats = _process_stats_row()
        rate = _avg_rate_row()

        cursor = self._setup_cursor_fetchone(conn, [
            order, prod, stats, rate, None,
        ])

        result = dao.calculate_order_stats(1)

        assert result is True
        conn.commit.assert_called_once()

    def test_calculate_partial_times(self, dao, conn):
        """部分时间：有 confirm_time 无 ship_time（order_cycle 为 None）"""
        order = _order_row(
            ship_time=None,
            receive_time=None,
        )
        prod = _production_row(plan_confirm_time=None, actual_end=None)
        stats = _process_stats_row()
        rate = _avg_rate_row()

        cursor = self._setup_cursor_fetchone(conn, [
            order, prod, stats, rate, None,
        ])

        result = dao.calculate_order_stats(1)

        assert result is True
        conn.commit.assert_called_once()

    def test_calculate_exception_rollback(self, dao, conn):
        """数据库异常时 rollback 并返回 False"""
        conn.cursor.side_effect = RuntimeError("数据库连接失败")

        result = dao.calculate_order_stats(1)

        assert result is False
        conn.rollback.assert_called_once()
        conn.close.assert_called_once()

    def test_calculate_qualified_rate_zero(self, dao, conn):
        """total_qty 为 0 时合格率为 0（避免除零）"""
        order = _order_row()
        prod = _production_row()
        empty = _process_empty_stats()
        rate = _avg_rate_row()

        cursor = self._setup_cursor_fetchone(conn, [
            order, prod, empty, rate, None,
        ])

        result = dao.calculate_order_stats(1)

        assert result is True
        conn.commit.assert_called_once()


# ═══════════════════════════════════════════════════════════
# get_order_stats
# ═══════════════════════════════════════════════════════════

class TestGetOrderStats:
    """ProductionStatsDAO.get_order_stats"""

    def test_get_order_stats_found(self, dao, conn):
        """统计数据存在"""
        stats_row = Row(order_id=1, order_no="PO-001", stats_status="已计算")
        cursor, _ = _make_cursor_and_conn()
        cursor.fetchone.return_value = stats_row
        conn.cursor.return_value = cursor

        result = dao.get_order_stats(1)

        assert result["order_id"] == 1
        assert result["stats_status"] == "已计算"
        conn.close.assert_called_once()

    def test_get_order_stats_not_found(self, dao, conn):
        """统计数据不存在"""
        cursor, _ = _make_cursor_and_conn()
        cursor.fetchone.return_value = None
        conn.cursor.return_value = cursor

        result = dao.get_order_stats(999)

        assert result == {}
        conn.close.assert_called_once()

    def test_get_order_stats_exception(self, dao, conn):
        """数据库异常"""
        conn.cursor.side_effect = RuntimeError("查询失败")

        result = dao.get_order_stats(1)

        assert result == {}
        conn.close.assert_called_once()


# ═══════════════════════════════════════════════════════════
# get_process_details
# ═══════════════════════════════════════════════════════════

class TestGetProcessDetails:
    """ProductionStatsDAO.get_process_details"""

    def test_get_details_found(self, dao, conn):
        """工序详情存在"""
        rows = [
            Row(process_name="编织", process_seq=1, duration_days=2.0, completed_qty=50,
                qualified_qty=48, calculated_qty=50, actual_used_qty=52,
                waste_rate=0.02, efficiency=0.92, worker="张三", machine_no="M001"),
            Row(process_name="焊接", process_seq=2, duration_days=1.5, completed_qty=50,
                qualified_qty=50, calculated_qty=50, actual_used_qty=50,
                waste_rate=0.0, efficiency=0.98, worker="李四", machine_no="M002"),
        ]
        cursor, _ = _make_cursor_and_conn()
        cursor.fetchall.return_value = rows
        conn.cursor.return_value = cursor

        result = dao.get_process_details(1)

        assert len(result) == 2
        assert result[0]["process_name"] == "编织"
        assert result[1]["process_seq"] == 2
        conn.close.assert_called_once()

    def test_get_details_empty(self, dao, conn):
        """无工序记录"""
        cursor, _ = _make_cursor_and_conn()
        cursor.fetchall.return_value = []
        conn.cursor.return_value = cursor

        result = dao.get_process_details(999)

        assert result == []
        conn.close.assert_called_once()

    def test_get_details_fetchall_none(self, dao, conn):
        """fetchall 返回 None"""
        cursor, _ = _make_cursor_and_conn()
        cursor.fetchall.return_value = None
        conn.cursor.return_value = cursor

        result = dao.get_process_details(1)

        assert result == []
        conn.close.assert_called_once()

    def test_get_details_exception(self, dao, conn):
        """数据库异常"""
        conn.cursor.side_effect = RuntimeError("查询工序失败")

        result = dao.get_process_details(1)

        assert result == []
        conn.close.assert_called_once()


# ═══════════════════════════════════════════════════════════
# calculate_all_orders_stats
# ═══════════════════════════════════════════════════════════

class TestCalculateAllOrdersStats:
    """ProductionStatsDAO.calculate_all_orders_stats"""

    def test_all_orders_success(self, dao, conn):
        """批量计算全部成功"""
        cursor, _ = _make_cursor_and_conn()
        cursor.fetchall.return_value = [Row(id=1), Row(id=2), Row(id=3)]
        conn.cursor.return_value = cursor

        with patch.object(dao, "calculate_order_stats",
                          return_value=True) as mock_calc:
            result = dao.calculate_all_orders_stats()

        assert result == {"success": 3, "fail": 0}
        assert mock_calc.call_count == 3
        assert mock_calc.call_args_list == [call(1), call(2), call(3)]
        conn.close.assert_called_once()

    def test_all_orders_partial_fail(self, dao, conn):
        """批量计算部分成功部分失败"""
        cursor, _ = _make_cursor_and_conn()
        cursor.fetchall.return_value = [Row(id=1), Row(id=2), Row(id=3)]
        conn.cursor.return_value = cursor

        side_effects = {1: True, 2: False, 3: True}

        def _mock_calc(order_id):
            return side_effects.get(order_id, False)

        with patch.object(dao, "calculate_order_stats",
                          side_effect=_mock_calc):
            result = dao.calculate_all_orders_stats()

        assert result == {"success": 2, "fail": 1}

    def test_all_orders_empty(self, dao, conn):
        """无已完成订单"""
        cursor, _ = _make_cursor_and_conn()
        cursor.fetchall.return_value = []
        conn.cursor.return_value = cursor

        with patch.object(dao, "calculate_order_stats") as mock_calc:
            result = dao.calculate_all_orders_stats()

        assert result == {"success": 0, "fail": 0}
        mock_calc.assert_not_called()

    def test_all_orders_exception(self, dao, conn):
        """数据库异常"""
        conn.cursor.side_effect = RuntimeError("批量查询失败")

        result = dao.calculate_all_orders_stats()

        assert result == {"success": 0, "fail": 0}
        conn.close.assert_called_once()


# ═══════════════════════════════════════════════════════════
# get_stats_summary
# ═══════════════════════════════════════════════════════════

class TestGetStatsSummary:
    """ProductionStatsDAO.get_stats_summary"""

    def test_summary_no_filters(self, dao, conn):
        """无日期过滤"""
        summary = Row(
            order_count=10, avg_order_cycle=5.0, avg_production_cycle=3.0,
            avg_total_cycle=8.0, avg_qualified_rate=96.5, avg_process_rate=94.2,
            avg_material_diff_rate=2.1, avg_efficiency=0.92,
        )
        cursor, _ = _make_cursor_and_conn()
        cursor.fetchone.return_value = summary
        conn.cursor.return_value = cursor

        result = dao.get_stats_summary()

        assert result["order_count"] == 10
        assert result["avg_qualified_rate"] == 96.5
        assert result["avg_efficiency"] == 0.92
        conn.close.assert_called_once()

    def test_summary_with_start_date(self, dao, conn):
        """指定开始日期"""
        summary = Row(order_count=5, avg_order_cycle=4.0, avg_production_cycle=3.0,
                      avg_total_cycle=7.0, avg_qualified_rate=97.0, avg_process_rate=95.0,
                      avg_material_diff_rate=1.5, avg_efficiency=0.95)
        cursor, _ = _make_cursor_and_conn()
        cursor.fetchone.return_value = summary
        conn.cursor.return_value = cursor

        result = dao.get_stats_summary(start_date="2026-06-01")

        assert result["order_count"] == 5
        # 验证 sql 中包含 calculated_at >= %s
        execute_args = cursor.execute.call_args
        assert "calculated_at >= %s" in execute_args[0][0]
        assert "2026-06-01" in execute_args[0][1]
        conn.close.assert_called_once()

    def test_summary_with_end_date(self, dao, conn):
        """指定结束日期"""
        summary = Row(order_count=8, avg_order_cycle=4.5, avg_production_cycle=2.5,
                      avg_total_cycle=7.5, avg_qualified_rate=96.0, avg_process_rate=93.0,
                      avg_material_diff_rate=2.0, avg_efficiency=0.90)
        cursor, _ = _make_cursor_and_conn()
        cursor.fetchone.return_value = summary
        conn.cursor.return_value = cursor

        result = dao.get_stats_summary(end_date="2026-06-30")

        assert result["order_count"] == 8
        execute_args = cursor.execute.call_args
        assert "calculated_at <= %s" in execute_args[0][0]
        assert "2026-06-30" in execute_args[0][1]
        conn.close.assert_called_once()

    def test_summary_with_both_dates(self, dao, conn):
        """同时指定开始和结束日期"""
        summary = Row(order_count=3, avg_order_cycle=3.0, avg_production_cycle=2.0,
                      avg_total_cycle=5.0, avg_qualified_rate=98.0, avg_process_rate=97.0,
                      avg_material_diff_rate=1.0, avg_efficiency=0.97)
        cursor, _ = _make_cursor_and_conn()
        cursor.fetchone.return_value = summary
        conn.cursor.return_value = cursor

        result = dao.get_stats_summary(start_date="2026-06-01", end_date="2026-06-30")

        assert result["order_count"] == 3
        execute_args = cursor.execute.call_args
        sql = execute_args[0][0]
        assert "calculated_at >= %s" in sql
        assert "calculated_at <= %s" in sql
        conn.close.assert_called_once()

    def test_summary_no_result(self, dao, conn):
        """无统计数据"""
        cursor, _ = _make_cursor_and_conn()
        cursor.fetchone.return_value = None
        conn.cursor.return_value = cursor

        result = dao.get_stats_summary()

        assert result == {}
        conn.close.assert_called_once()

    def test_summary_exception(self, dao, conn):
        """数据库异常"""
        conn.cursor.side_effect = RuntimeError("汇总查询失败")

        result = dao.get_stats_summary()

        assert result == {}
        conn.close.assert_called_once()
