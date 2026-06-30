# -*- coding: utf-8 -*-
"""
测试 alert.py - 逾期预警模型（覆盖率 12.12% → ~90%+）
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


class TestAlertDAO:

    # ---- 辅助方法 ----
    def _mock_patch(self):
        """返回 (patcher, mock_conn, mock_cursor)"""
        patcher = patch('models.alert.get_connection')
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value = mock_cursor
        patcher.start().return_value = mock_conn
        return patcher, mock_conn, mock_cursor

    def _make_row(self, data: dict):
        """模拟 fetchall/fetchone 返回的可 dict() 转换的行"""
        return data

    # ============================================================
    # get_overdue_orders
    # ============================================================
    def test_get_overdue_orders_empty(self):
        """无逾期数据返回空列表"""
        from models.alert import AlertDAO
        patcher, mock_conn, mock_cursor = self._mock_patch()
        try:
            mock_cursor.fetchall.return_value = []
            result = AlertDAO.get_overdue_orders(0)
            assert result == {"overdue": [], "warning": []}
            assert mock_cursor.execute.call_count == 2  # overdue + warning 两条 SQL
        finally:
            patcher.stop()

    def test_get_overdue_orders_with_overdue_dateobj(self):
        """日期对象格式的逾期订单"""
        from models.alert import AlertDAO
        patcher, mock_conn, mock_cursor = self._mock_patch()
        try:
            overdue_date = datetime.now() - timedelta(days=5)
            mock_cursor.fetchall.return_value = [
                self._make_row({
                    'delivery_date': overdue_date,
                    'order_no': 'ORD-001', 'status': '进行中',
                    'production_status': '正常',
                })
            ]
            result = AlertDAO.get_overdue_orders(0)
            assert len(result["overdue"]) == 1
            assert result["overdue"][0]["overdue_days"] == 5
            assert result["warning"] == []
        finally:
            patcher.stop()

    def test_get_overdue_orders_with_overdue_str(self):
        """字符串格式的逾期订单"""
        from models.alert import AlertDAO
        patcher, mock_conn, mock_cursor = self._mock_patch()
        try:
            past_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d 10:00:00")
            mock_cursor.fetchall.return_value = [
                self._make_row({
                    'delivery_date': past_date,
                    'order_no': 'ORD-002', 'status': '进行中',
                })
            ]
            result = AlertDAO.get_overdue_orders(0)
            assert len(result["overdue"]) == 1
            assert result["overdue"][0]["overdue_days"] == 10
        finally:
            patcher.stop()

    def test_get_overdue_orders_future_date_not_overdue(self):
        """未来的交货日期不计入逾期"""
        from models.alert import AlertDAO
        patcher, mock_conn, mock_cursor = self._mock_patch()
        try:
            future_date = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
            mock_cursor.fetchall.return_value = [
                self._make_row({
                    'delivery_date': future_date,
                    'order_no': 'ORD-003', 'status': '进行中',
                })
            ]
            result = AlertDAO.get_overdue_orders(0)
            assert result["overdue"] == []
        finally:
            patcher.stop()

    def test_get_overdue_orders_bad_date_skipped(self):
        """非法的日期格式应被跳过"""
        from models.alert import AlertDAO
        patcher, mock_conn, mock_cursor = self._mock_patch()
        try:
            mock_cursor.fetchall.return_value = [
                self._make_row({
                    'delivery_date': '0000-00-00',
                    'order_no': 'ORD-BAD', 'status': '进行中',
                })
            ]
            result = AlertDAO.get_overdue_orders(0)
            assert result["overdue"] == []
        finally:
            patcher.stop()

    def test_get_overdue_orders_strptime_exception(self):
        """字符串日期格式错误导致 strptime 抛异常→continue（覆盖L45-46 except分支）"""
        from models.alert import AlertDAO
        patcher, mock_conn, mock_cursor = self._mock_patch()
        try:
            # 非 "0000" 开头但格式不对 → strptime 抛 ValueError
            mock_cursor.fetchall.return_value = [
                self._make_row({
                    'delivery_date': '2024-13-01',  # 月份13，无效
                    'order_no': 'ORD-BAD2', 'status': '进行中',
                })
            ]
            result = AlertDAO.get_overdue_orders(0)
            assert result["overdue"] == []
        finally:
            patcher.stop()

    def test_get_warning_orders_else_continue(self):
        """warning 分支 delivery_date 非 date 非 str → else continue（覆盖L81）"""
        from models.alert import AlertDAO
        patcher, mock_conn, mock_cursor = self._mock_patch()
        try:
            today = datetime.now().date()
            normal_date = today.strftime("%Y-%m-%d")
            # overdue 查到一个正常订单
            # warning 查到 delivery_date 为 int — 既无 .date() 也不是 str
            mock_cursor.fetchall.side_effect = [
                [self._make_row({
                    'delivery_date': normal_date,
                    'order_no': 'ORD-NORM', 'status': '进行中',
                })],
                [self._make_row({
                    'delivery_date': 12345,  # int → else: continue
                    'order_no': 'ORD-WARN', 'status': '进行中',
                })],
            ]
            result = AlertDAO.get_overdue_orders(days=5)
            assert result["warning"] == []
        finally:
            patcher.stop()

    def test_get_warning_orders(self):
        """即将到期预警测试（包含 warning 分支）"""
        from models.alert import AlertDAO
        patcher, mock_conn, mock_cursor = self._mock_patch()
        try:
            today = datetime.now().date()
            # overdue SQL 返回一个正常订单（不过期）
            normal_date = today.strftime("%Y-%m-%d")
            # warning SQL 返回一个即将到期订单
            warning_date = (today + timedelta(days=2)).strftime("%Y-%m-%d")

            # 第一次 fetchall（overdue查询）→ 无逾期
            # 第二次 fetchall（warning查询）→ 一个即将到期
            mock_cursor.fetchall.side_effect = [
                [self._make_row({
                    'delivery_date': normal_date,
                    'order_no': 'ORD-010', 'status': '进行中',
                })],
                [self._make_row({
                    'delivery_date': warning_date,
                    'order_no': 'ORD-011', 'status': '进行中',
                })],
            ]
            result = AlertDAO.get_overdue_orders(days=5)
            assert result["overdue"] == []
            assert len(result["warning"]) == 1
            assert result["warning"][0]["remain_days"] == 2
        finally:
            patcher.stop()

    def test_get_warning_orders_out_of_range(self):
        """超预警范围的订单不计入 warning"""
        from models.alert import AlertDAO
        patcher, mock_conn, mock_cursor = self._mock_patch()
        try:
            today = datetime.now().date()
            today_str = today.strftime("%Y-%m-%d")
            far_future = (today + timedelta(days=10)).strftime("%Y-%m-%d")

            mock_cursor.fetchall.side_effect = [
                [self._make_row({
                    'delivery_date': today_str,
                    'order_no': 'ORD-020', 'status': '进行中',
                })],
                [self._make_row({
                    'delivery_date': far_future,
                    'order_no': 'ORD-021', 'status': '进行中',
                })],
            ]
            result = AlertDAO.get_overdue_orders(days=5)
            # 今天到期不过期（overdue_days = 0，不大于0）
            assert result["overdue"] == []
            # 10天后超过预警范围（days=5），remain_days=10 > 5
            assert result["warning"] == []
        finally:
            patcher.stop()

    # ============================================================
    # get_overdue_processes
    # ============================================================
    def test_get_overdue_processes_empty(self):
        """无逾期工序"""
        from models.alert import AlertDAO
        patcher, mock_conn, mock_cursor = self._mock_patch()
        try:
            mock_cursor.fetchall.return_value = []
            result = AlertDAO.get_overdue_processes()
            assert result == []
        finally:
            patcher.stop()

    def test_get_overdue_processes_with_overdue(self):
        """存在逾期工序"""
        from models.alert import AlertDAO
        patcher, mock_conn, mock_cursor = self._mock_patch()
        try:
            past_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            mock_cursor.fetchall.return_value = [
                self._make_row({
                    'planned_date': past_date,
                    'order_no': 'ORD-030', 'status': '待开始',
                })
            ]
            result = AlertDAO.get_overdue_processes()
            assert len(result) == 1
            assert result[0]["overdue_days"] == 7
        finally:
            patcher.stop()

    def test_get_overdue_processes_future_not_overdue(self):
        """未来计划不计入逾期"""
        from models.alert import AlertDAO
        patcher, mock_conn, mock_cursor = self._mock_patch()
        try:
            future_date = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
            mock_cursor.fetchall.return_value = [
                self._make_row({
                    'planned_date': future_date,
                    'order_no': 'ORD-031', 'status': '待开始',
                })
            ]
            result = AlertDAO.get_overdue_processes()
            assert result == []
        finally:
            patcher.stop()

    def test_get_overdue_processes_no_planned_date(self):
        """无计划日期不计逾期"""
        from models.alert import AlertDAO
        patcher, mock_conn, mock_cursor = self._mock_patch()
        try:
            mock_cursor.fetchall.return_value = [
                self._make_row({
                    'planned_date': None,
                    'order_no': 'ORD-032', 'status': '待开始',
                })
            ]
            result = AlertDAO.get_overdue_processes()
            assert result == []
        finally:
            patcher.stop()

    def test_get_overdue_processes_with_dateobj(self):
        """planned_date 为 date 对象（覆盖 L121 hasattr branch）"""
        from models.alert import AlertDAO
        patcher, mock_conn, mock_cursor = self._mock_patch()
        try:
            past_date = (datetime.now() - timedelta(days=3))
            mock_cursor.fetchall.return_value = [
                self._make_row({
                    'planned_date': past_date,
                    'order_no': 'ORD-DT', 'status': '待开始',
                })
            ]
            result = AlertDAO.get_overdue_processes()
            assert len(result) == 1
            assert result[0]["overdue_days"] == 3
        finally:
            patcher.stop()

    def test_get_overdue_processes_strptime_exception(self):
        """planned_date 字符串格式错误 → except plan_date=None（覆盖 L125-126）"""
        from models.alert import AlertDAO
        patcher, mock_conn, mock_cursor = self._mock_patch()
        try:
            mock_cursor.fetchall.return_value = [
                self._make_row({
                    'planned_date': 'invalid-date-str',
                    'order_no': 'ORD-BAD3', 'status': '待开始',
                })
            ]
            result = AlertDAO.get_overdue_processes()
            assert result == []
        finally:
            patcher.stop()

    def test_get_overdue_processes_planned_date_not_date_nor_str(self):
        """planned_date 非 date 非 str → else plan_date=None（覆盖 L128）"""
        from models.alert import AlertDAO
        patcher, mock_conn, mock_cursor = self._mock_patch()
        try:
            mock_cursor.fetchall.return_value = [
                self._make_row({
                    'planned_date': 99999,  # int → else: plan_date = None
                    'order_no': 'ORD-INT', 'status': '待开始',
                })
            ]
            result = AlertDAO.get_overdue_processes()
            assert result == []
        finally:
            patcher.stop()

    # ============================================================
    # get_low_inventory_alerts
    # ============================================================
    def test_get_low_inventory_empty(self):
        """无库存预警"""
        from models.alert import AlertDAO
        patcher, mock_conn, mock_cursor = self._mock_patch()
        try:
            mock_cursor.fetchall.return_value = []
            result = AlertDAO.get_low_inventory_alerts()
            assert result == []
        finally:
            patcher.stop()

    def test_get_low_inventory_with_alerts(self):
        """存在库存预警"""
        from models.alert import AlertDAO
        patcher, mock_conn, mock_cursor = self._mock_patch()
        try:
            mock_cursor.fetchall.return_value = [
                self._make_row({'id': 1, 'name': '钢材', 'quantity': 10, 'warning_qty': 50, 'alert_level': '库存预警'}),
                self._make_row({'id': 2, 'name': '焊条', 'quantity': 0, 'warning_qty': 20, 'alert_level': '库存不足'}),
            ]
            result = AlertDAO.get_low_inventory_alerts()
            assert len(result) == 2
            assert result[0]['name'] == '钢材'
        finally:
            patcher.stop()

    # ============================================================
    # get_all_alerts
    # ============================================================
    def test_get_all_alerts(self):
        """get_all_alerts 汇总所有预警"""
        from models.alert import AlertDAO
        # mock 三个子方法
        with patch.object(AlertDAO, 'get_overdue_orders', return_value={
            "overdue": [{"order_no": "ORD-001"}],
            "warning": [{"order_no": "ORD-002"}],
        }) as mock_overdue, \
             patch.object(AlertDAO, 'get_low_inventory_alerts', return_value=[{"name": "钢材"}]) as mock_inv, \
             patch('models.alert.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2026, 6, 1, 12, 0, 0)
            mock_dt.strftime = datetime.strftime

            result = AlertDAO.get_all_alerts(days=3)
            assert len(result["overdue_orders"]) == 1
            assert len(result["warning_orders"]) == 1
            assert len(result["low_inventory"]) == 1
            assert result["timestamp"] == "2026-06-01 12:00:00"
            mock_overdue.assert_called()
            mock_inv.assert_called_once()


# ============================================================
# init_alert_table
# ============================================================
class TestInitAlertTable:

    def test_init_alert_table_creates_table(self):
        """init_alert_table 执行建表语句"""
        from models.alert import init_alert_table
        with patch('models.alert.get_connection') as mock_gc:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_gc.return_value = mock_conn

            init_alert_table()

            mock_cursor.execute.assert_called_once()
            sql = mock_cursor.execute.call_args[0][0]
            assert "CREATE TABLE IF NOT EXISTS" in sql
            assert "alert_records" in sql
            mock_conn.commit.assert_called_once()
