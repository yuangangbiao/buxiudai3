# -*- coding: utf-8 -*-
"""
models/process.py ProcessDAO 单元测试（已验证 API）
"""
import pytest
from unittest.mock import patch, MagicMock


class TestProcessDAO:
    """ProcessDAO 测试 - 基于实际 API"""

    @pytest.fixture(autouse=True)
    def setup(self):
        import sys
        for m in list(sys.modules.keys()):
            if m.startswith('models.process'):
                del sys.modules[m]
        self.mock_cursor = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor
        self.mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=self.mock_cursor)
        self.mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

    def _patch(self):
        # 先 patch 再删除并重新导入，确保 from models.database import get_connection 拿到 Mock
        p = patch('models.database.get_connection', return_value=self.mock_conn)
        p.start()
        import sys
        for m in list(sys.modules.keys()):
            if m.startswith('models.process'):
                del sys.modules[m]
        return p

    def test_create_process_record(self):
        self.mock_cursor.lastrowid = 50
        p = self._patch()
        from models.process import ProcessDAO
        result = ProcessDAO().create({"order_id": 1, "process_name": "编织"})
        assert result == 50
        p.stop()

    def test_get_by_id(self):
        self.mock_cursor.fetchone.return_value = {"id": 1, "process_name": "质检"}
        p = self._patch()
        from models.process import ProcessDAO
        result = ProcessDAO().get_by_id(1)
        assert result["id"] == 1
        p.stop()

    def test_get_by_id_not_found(self):
        self.mock_cursor.fetchone.return_value = None
        p = self._patch()
        from models.process import ProcessDAO
        result = ProcessDAO().get_by_id(999)
        assert result is None
        p.stop()

    def test_get_by_order(self):
        self.mock_cursor.fetchall.return_value = [{"id": 1}, {"id": 2}]
        p = self._patch()
        from models.process import ProcessDAO
        result = ProcessDAO().get_by_order(1)
        assert len(result) == 2
        p.stop()

    def test_get_by_production(self):
        self.mock_cursor.fetchall.return_value = [{"id": 1}]
        p = self._patch()
        from models.process import ProcessDAO
        result = ProcessDAO().get_by_production(10)
        assert len(result) == 1
        p.stop()

    def test_update_record(self):
        self.mock_cursor.rowcount = 1
        p = self._patch()
        from models.process import ProcessDAO
        result = ProcessDAO().update_record(1, {"completed_qty": 50})
        assert result is True
        p.stop()

    def test_delete_record(self):
        self.mock_cursor.rowcount = 1
        p = self._patch()
        from models.process import ProcessDAO
        result = ProcessDAO().delete(1)
        assert result is True
        p.stop()

    def test_delete_record_not_found(self):
        self.mock_cursor.rowcount = 0
        p = self._patch()
        from models.process import ProcessDAO
        result = ProcessDAO().delete(999)
        assert result is False
        p.stop()

    def test_get_worker_stats(self):
        self.mock_cursor.fetchall.return_value = [{"worker_id": "W1", "total": 500}]
        p = self._patch()
        from models.process import ProcessDAO
        result = ProcessDAO().get_worker_stats(date_from="2026-01-01")
        assert len(result) == 1
        p.stop()

    def test_get_worker_stats_no_filter(self):
        self.mock_cursor.fetchall.return_value = []
        p = self._patch()
        from models.process import ProcessDAO
        result = ProcessDAO().get_worker_stats()
        assert isinstance(result, list)
        p.stop()

    def test_get_progress_no_record(self):
        self.mock_cursor.fetchone.return_value = None
        p = self._patch()
        from models.process import ProcessDAO
        result = ProcessDAO().get_progress(999)
        assert result == 0
        p.stop()

    def test_get_today_completed_no_record(self):
        self.mock_cursor.fetchone.return_value = None
        p = self._patch()
        from models.process import ProcessDAO
        result = ProcessDAO().get_today_completed(999)
        assert result == 0
        p.stop()

    def test_update_record_multiple_fields(self):
        self.mock_cursor.rowcount = 1
        p = self._patch()
        from models.process import ProcessDAO
        result = ProcessDAO().update_record(1, {
            "completed_qty": 50,
            "defect_qty": 2
        })
        assert result is True
        p.stop()

    def test_get_by_order_empty(self):
        self.mock_cursor.fetchall.return_value = []
        p = self._patch()
        from models.process import ProcessDAO
        result = ProcessDAO().get_by_order(999)
        assert len(result) == 0
        p.stop()

    # ── update_record 状态流转场景 ──────────────────────────

    def test_update_record_pending_to_in_progress(self):
        """PENDING→IN_PROGRESS: 触发 start_time=NOW, 不触发 end_time"""
        old_rec = {"status": "待开始", "order_id": 1, "production_id": 100,
                    "start_time": None, "end_time": None}
        self.mock_cursor.fetchone.return_value = old_rec
        p = self._patch()
        with patch('models.process.log_status_change'):
            from models.process import ProcessDAO
            from constants import ProcessStatus
            result = ProcessDAO().update_record(1, {"status": ProcessStatus.IN_PROGRESS.value})
        assert result is True
        p.stop()
        # 验证 process_records UPDATE SQL 包含 start_time=NOW()
        all_executes = [c[0] for c in self.mock_cursor.execute.call_args_list]
        process_update = [args for args in all_executes if 'UPDATE process_records' in str(args)]
        assert process_update, "应有 process_records UPDATE"
        update_sql = process_update[0][0]
        assert 'start_time=NOW()' in update_sql, f"应追加 start_time=NOW(), 实际: {update_sql}"
        assert 'end_time=NOW()' not in update_sql, "不应追加 end_time=NOW()"

    def test_update_record_pending_to_completed(self):
        """PENDING→COMPLETED: 触发 start_time=NOW + end_time=NOW"""
        old_rec = {"status": "待开始", "order_id": 1, "production_id": 100,
                    "start_time": None, "end_time": None}
        self.mock_cursor.fetchone.side_effect = [
            old_rec,
            {"cnt": 0}  # 没有未完成工序
        ]
        p = self._patch()
        with patch('models.process.log_status_change'):
            from models.process import ProcessDAO
            from constants import ProcessStatus
            result = ProcessDAO().update_record(1, {"status": ProcessStatus.COMPLETED.value})
        assert result is True
        p.stop()
        all_executes = [c[0] for c in self.mock_cursor.execute.call_args_list]
        process_update = [args for args in all_executes if 'UPDATE process_records' in str(args)]
        assert process_update, "应有 process_records UPDATE"
        update_sql = process_update[0][0]
        assert 'start_time=NOW()' in update_sql
        assert 'end_time=NOW()' in update_sql

    def test_update_record_completed_all_done(self):
        """工序全部完成 → 更新 production_orders + orders 到 QC 状态"""
        old_rec = {"status": "待开始", "order_id": 1, "production_id": 100,
                    "start_time": None, "end_time": None}
        self.mock_cursor.fetchone.side_effect = [
            old_rec,
            {"cnt": 0}  # 全部完成
        ]
        p = self._patch()
        with patch('models.process.log_status_change'):
            from models.process import ProcessDAO
            from constants import ProcessStatus
            result = ProcessDAO().update_record(1, {"status": ProcessStatus.COMPLETED.value})
        assert result is True
        p.stop()
        all_sqls = [c[0][0] for c in self.mock_cursor.execute.call_args_list]
        prod_update = [s for s in all_sqls if 'production_orders' in s and 'status' in s]
        order_update = [s for s in all_sqls if 'UPDATE orders' in s]
        assert prod_update, "应更新 production_orders"
        assert order_update, "应更新 orders"

    def test_update_record_completed_with_unfinished(self):
        """当前完成但还有未完成工序 → 只设置 actual_start，不触发 QC"""
        old_rec = {"status": "待开始", "order_id": 1, "production_id": 100,
                    "start_time": None, "end_time": None}
        self.mock_cursor.fetchone.side_effect = [
            old_rec,
            {"cnt": 2}  # 还有 2 条未完成
        ]
        p = self._patch()
        with patch('models.process.log_status_change'):
            from models.process import ProcessDAO
            from constants import ProcessStatus
            result = ProcessDAO().update_record(1, {"status": ProcessStatus.COMPLETED.value})
        assert result is True
        p.stop()
        all_sqls = [c[0][0] for c in self.mock_cursor.execute.call_args_list]
        prod_updates = [s for s in all_sqls if 'UPDATE production_orders' in s]
        orders_updates = [s for s in all_sqls if 'UPDATE orders' in s]
        assert prod_updates, "应更新 production_orders"
        assert any("actual_start" in s for s in prod_updates)
        # orders 不应包含 QC (因为还有未完成工序)
        assert not any("QC" in s for s in orders_updates), "不应将 orders 更新为 QC"

    def test_update_record_in_progress_first_report(self):
        """IN_PROGRESS 第一次报工 → 更新 production_orders/orders"""
        old_rec = {"status": "待开始", "order_id": 1, "production_id": 100,
                    "start_time": None, "end_time": None}
        self.mock_cursor.fetchone.return_value = old_rec
        p = self._patch()
        with patch('models.process.log_status_change'):
            from models.process import ProcessDAO
            from constants import ProcessStatus
            result = ProcessDAO().update_record(1, {"status": ProcessStatus.IN_PROGRESS.value})
        assert result is True
        p.stop()
        all_sqls = [c[0][0] for c in self.mock_cursor.execute.call_args_list]
        prod_updates = [s for s in all_sqls if 'UPDATE production_orders' in s]
        assert prod_updates, "应更新 production_orders"
        assert any("actual_start" in s for s in prod_updates)

    def test_update_record_no_status_change_skips_log(self):
        """状态未变更 → 不调用 log_status_change（且不走分支）"""
        old_rec = {"status": "进行中", "order_id": 1, "production_id": 100,
                    "start_time": None, "end_time": None}
        self.mock_cursor.fetchone.return_value = old_rec
        p = self._patch()
        with patch('models.process.log_status_change') as mock_log:
            from models.process import ProcessDAO
            from constants import ProcessStatus
            result = ProcessDAO().update_record(1, {"status": ProcessStatus.IN_PROGRESS.value})
            assert result is True
            mock_log.assert_not_called()
        p.stop()

    # ── get_worker_stats date_to 分支 ──────────────────────

    def test_get_worker_stats_with_date_to(self):
        """get_worker_stats 带 date_to 参数"""
        self.mock_cursor.fetchall.return_value = [
            {"worker": "W1", "total_hours": 8, "total_qty": 100, "task_count": 2}
        ]
        p = self._patch()
        from models.process import ProcessDAO
        result = ProcessDAO().get_worker_stats(date_from="2026-01-01", date_to="2026-06-01")
        assert len(result) == 1
        p.stop()

    # ── get_today_completed_batch ──────────────────────────

    def test_get_today_completed_batch_empty(self):
        """空列表返回 {}"""
        p = self._patch()
        from models.process import ProcessDAO
        result = ProcessDAO().get_today_completed_batch([])
        assert result == {}
        p.stop()

    def test_get_today_completed_batch_with_data(self):
        """批量查询今日完成量"""
        self.mock_cursor.fetchall.return_value = [
            {"id": 1, "completed_qty": 50},
            {"id": 2, "completed_qty": 30}
        ]
        p = self._patch()
        from models.process import ProcessDAO
        result = ProcessDAO().get_today_completed_batch([1, 2])
        assert result == {1: 50, 2: 30}
        p.stop()

    def test_get_today_completed_batch_single(self):
        """批量查询单个记录"""
        self.mock_cursor.fetchall.return_value = [
            {"id": 5, "completed_qty": 100}
        ]
        p = self._patch()
        from models.process import ProcessDAO
        result = ProcessDAO().get_today_completed_batch([5])
        assert result == {5: 100}
        p.stop()

    def test_get_today_completed_batch_no_match(self):
        """批量查询无匹配"""
        self.mock_cursor.fetchall.return_value = []
        p = self._patch()
        from models.process import ProcessDAO
        result = ProcessDAO().get_today_completed_batch([999])
        assert result == {}
        p.stop()

