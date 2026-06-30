# -*- coding: utf-8 -*-
"""
models/process.py ProcessDAO 深度测试 — 全覆盖剩余分支（73%→100%）
"""
import pytest
from unittest.mock import patch, MagicMock, call
from constants import ProcessStatus, OrderStatus, ProductionStatus


class TestProcessUpdateRecord:
    """ProcessDAO.update_record — 核心业务逻辑全覆盖"""

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
        # process.py 用 from models.database import get_connection
        # 所以必须 patch models.process.get_connection
        self.conn_p = patch('models.process.get_connection', return_value=self.mock_conn)
        self.conn_p.start()
        self.log_p = patch('models.process.log_status_change')
        self.log_p.start()
        from models.process import ProcessDAO
        self.dao = ProcessDAO()
        yield
        self.log_p.stop()
        self.conn_p.stop()

    def _setup_old_record(self, status=ProcessStatus.PENDING.value, order_id=1, production_id=10):
        """设置旧记录返回"""
        self.mock_cursor.fetchone.return_value = {
            "status": status, "order_id": order_id, "production_id": production_id,
            "start_time": None, "end_time": None,
        }

    def _make_row(self, data):
        """通用 mock row"""
        m = MagicMock()
        m.__getitem__ = lambda s, k: data.get(k) if isinstance(data, dict) else data
        return m

    # ── 工序全部完成 → 更新 production_orders COMPLETED, orders QC ──

    def test_complete_all_processes(self):
        """工序全部完成：更新 production_orders=COMPLETED, orders=QC"""
        # fetchone 第1次：SELECT status,order_id,production_id,start_time,end_time
        # 第2次：SELECT COUNT(*) as cnt FROM process_records
        # 源码用 isinstance + else: unfinished[0] if unfinished else 0
        # 用 tuple (0,) 让 else 分支生效
        self.mock_cursor.fetchone.side_effect = [
            {"status": ProcessStatus.IN_PROGRESS.value, "order_id": 1, "production_id": 10,
             "start_time": None, "end_time": None},
            (0,),  # 未完成工序=0 (tuple, else分支)
        ]

        result = self.dao.update_record(1, {"status": ProcessStatus.COMPLETED.value})

        assert result is True
        # 验证 conn.commit 被调
        assert self.mock_conn.commit.call_count >= 1

    def test_complete_partial_processes(self):
        """工序部分完成（还有未完成）：更新 production_orders=IN_PROGRESS, orders=PRODUCTION"""
        self.mock_cursor.fetchone.side_effect = [
            {"status": ProcessStatus.IN_PROGRESS.value, "order_id": 1, "production_id": 10,
             "start_time": None, "end_time": None},
            {"cnt": 2},  # 还有2个未完成
        ]

        result = self.dao.update_record(1, {"status": ProcessStatus.COMPLETED.value})

        assert result is True
        assert self.mock_conn.commit.call_count >= 1

    def test_start_in_progress_process(self):
        """工序变更为进行中：更新 production_orders=IN_PROGRESS, orders=PRODUCTION"""
        self.mock_cursor.fetchone.return_value = {
            "status": ProcessStatus.PENDING.value, "order_id": 1, "production_id": 10,
            "start_time": None, "end_time": None,
        }

        result = self.dao.update_record(1, {"status": ProcessStatus.IN_PROGRESS.value})

        assert result is True
        assert self.mock_conn.commit.call_count >= 1

    def test_update_no_status_change(self):
        """更新其他字段，状态无变化"""
        self.mock_cursor.fetchone.return_value = {
            "status": ProcessStatus.IN_PROGRESS.value, "order_id": 1, "production_id": 10,
            "start_time": "2026-01-01 08:00:00", "end_time": None,
        }

        result = self.dao.update_record(1, {"completed_qty": 100})

        assert result is True

    def test_update_record_not_found(self):
        """记录不存在时仍可更新（不会报错）"""
        self.mock_cursor.fetchone.return_value = None

        result = self.dao.update_record(999, {"completed_qty": 50})

        assert result is True

    def test_complete_all_processes_dict_row_get(self):
        """工序全部完成：row 是 dict 类型用 get"""
        class DictRow(dict):
            pass
        row = DictRow({"cnt": 0})
        self.mock_cursor.fetchone.side_effect = [
            {"status": ProcessStatus.IN_PROGRESS.value, "order_id": 1, "production_id": 10,
             "start_time": None, "end_time": None},
            row,  # 未完成工序=0 (dict类型)
        ]

        result = self.dao.update_record(1, {"status": ProcessStatus.COMPLETED.value})

        assert result is True


class TestProcessGetProgress:
    """get_progress 剩余分支（源码用 row[0]，MySQL tuple类型）"""

    @pytest.fixture(autouse=True)
    def setup(self):
        import sys
        for m in list(sys.modules.keys()):
            if m.startswith('models.process'):
                del sys.modules[m]
        self.mock_cursor = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor
        self.p = patch('models.database.get_connection', return_value=self.mock_conn)
        self.p.start()
        from models.process import ProcessDAO
        self.dao = ProcessDAO()
        yield
        self.p.stop()

    def test_progress_normal(self):
        """正常进度计算：5个工序中3个完成"""
        # 源码用 row[0]，MySQL默认返回tuple
        self.mock_cursor.fetchone.side_effect = [(5,), (3,)]
        result = self.dao.get_progress(1)
        assert result == 60.0

    def test_progress_all_done(self):
        """全部完成"""
        self.mock_cursor.fetchone.side_effect = [(4,), (4,)]
        result = self.dao.get_progress(1)
        assert result == 100.0

    def test_progress_none_done(self):
        """完成0个"""
        self.mock_cursor.fetchone.side_effect = [(3,), (0,)]
        result = self.dao.get_progress(1)
        assert result == 0.0


class TestProcessGetTodayCompleted:
    """get_today_completed 剩余分支"""

    @pytest.fixture(autouse=True)
    def setup(self):
        import sys
        for m in list(sys.modules.keys()):
            if m.startswith('models.process'):
                del sys.modules[m]
        self.mock_cursor = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor
        self.p = patch('models.database.get_connection', return_value=self.mock_conn)
        self.p.start()
        from models.process import ProcessDAO
        self.dao = ProcessDAO()
        yield
        self.p.stop()

    def test_today_completed_found(self):
        """找到记录返回完成量"""
        row = MagicMock()
        row.__getitem__ = lambda s, k: 150
        self.mock_cursor.fetchone.return_value = row
        result = self.dao.get_today_completed(1)
        assert result == 150


class TestProcessGetWorkerStats:
    """get_worker_stats 剩余分支"""

    @pytest.fixture(autouse=True)
    def setup(self):
        import sys
        for m in list(sys.modules.keys()):
            if m.startswith('models.process'):
                del sys.modules[m]
        self.mock_cursor = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor
        self.p = patch('models.database.get_connection', return_value=self.mock_conn)
        self.p.start()
        from models.process import ProcessDAO
        self.dao = ProcessDAO()
        yield
        self.p.stop()

    def test_worker_stats_date_range(self):
        """date_from + date_to 完整时间范围"""
        self.mock_cursor.fetchall.return_value = [{"worker": "张三", "total_hours": 40}]
        result = self.dao.get_worker_stats(date_from="2026-01-01", date_to="2026-01-31")
        assert len(result) == 1


class TestProcessGetTodayCompletedBatch:
    """get_today_completed_batch 全覆盖"""

    @pytest.fixture(autouse=True)
    def setup(self):
        import sys
        for m in list(sys.modules.keys()):
            if m.startswith('models.process'):
                del sys.modules[m]
        self.mock_cursor = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor
        self.p = patch('models.database.get_connection', return_value=self.mock_conn)
        self.p.start()
        from models.process import ProcessDAO
        self.dao = ProcessDAO()
        yield
        self.p.stop()

    def test_batch_empty(self):
        """空列表返回空字典"""
        result = self.dao.get_today_completed_batch([])
        assert result == {}

    def test_batch_multiple_records(self):
        """批量获取多个记录"""
        row1 = MagicMock()
        row1.__getitem__ = lambda s, k: 101 if k == "id" else 50
        row2 = MagicMock()
        row2.__getitem__ = lambda s, k: 102 if k == "id" else 30
        self.mock_cursor.fetchall.return_value = [row1, row2]

        result = self.dao.get_today_completed_batch([101, 102])

        assert result == {101: 50, 102: 30}

    def test_batch_single(self):
        """单条记录"""
        row = MagicMock()
        row.__getitem__ = lambda s, k: 1 if k == "id" else 100
        self.mock_cursor.fetchall.return_value = [row]

        result = self.dao.get_today_completed_batch([1])

        assert result == {1: 100}

    def test_batch_no_results(self):
        """无结果"""
        self.mock_cursor.fetchall.return_value = []

        result = self.dao.get_today_completed_batch([999])

        assert result == {}
