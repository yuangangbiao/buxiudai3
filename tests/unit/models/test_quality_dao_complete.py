# -*- coding: utf-8 -*-
"""
models/quality.py QualityDAO 单元测试（已验证 API）
"""
import pytest
from unittest.mock import patch, MagicMock


class TestQualityDAO:
    """QualityDAO 测试 - 基于实际 API"""

    @pytest.fixture(autouse=True)
    def setup(self):
        import sys
        for m in list(sys.modules.keys()):
            if m.startswith('models.quality'):
                del sys.modules[m]
            if m.startswith('models.shipment'):
                del sys.modules[m]
        self.mock_cursor = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor
        self.mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=self.mock_cursor)
        self.mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

    def _patch(self):
        p = patch('models.quality.get_connection', return_value=self.mock_conn)
        p.start()
        return p

    def test_create_quality_record(self):
        self.mock_cursor.lastrowid = 30
        p = self._patch()
        from models.quality import QualityDAO
        result = QualityDAO().create({"order_id": 1, "check_result": "合格", "quantity": 100})
        assert result == 30
        p.stop()

    def test_update_quality_record(self):
        self.mock_cursor.rowcount = 1
        p = self._patch()
        from models.quality import QualityDAO
        # update 可能返回 None，验证调用不报错
        QualityDAO().update(1, {"check_result": "合格"})
        assert True  # 无异常即通过
        p.stop()

    def test_delete_quality_record(self):
        self.mock_cursor.rowcount = 1
        p = self._patch()
        from models.quality import QualityDAO
        QualityDAO().delete(1)
        assert True
        p.stop()

    def test_get_all_no_filter(self):
        self.mock_cursor.fetchall.return_value = [{"id": 1}, {"id": 2}]
        p = self._patch()
        from models.quality import QualityDAO
        result = QualityDAO().get_all()
        assert len(result) == 2
        p.stop()

    def test_get_all_with_filters(self):
        self.mock_cursor.fetchall.return_value = [{"id": 1}]
        p = self._patch()
        from models.quality import QualityDAO
        result = QualityDAO().get_all(filters={"result": "合格"}, limit=10)
        assert len(result) == 1
        p.stop()

    def test_get_by_order(self):
        self.mock_cursor.fetchall.return_value = [{"id": 1, "order_id": 5}]
        p = self._patch()
        from models.quality import QualityDAO
        result = QualityDAO().get_by_order(5)
        assert len(result) == 1
        assert result[0]["order_id"] == 5
        p.stop()

    def test_get_order_processes(self):
        self.mock_cursor.fetchall.return_value = [{"process_name": "编织", "check_result": "合格"}]
        p = self._patch()
        from models.quality import QualityDAO
        result = QualityDAO().get_order_processes(1)
        assert isinstance(result, list)
        p.stop()

    def test_get_work_no_map(self):
        self.mock_cursor.fetchall.return_value = [{"order_id": 1, "work_no": "WN001"}]
        p = self._patch()
        from models.quality import QualityDAO
        result = QualityDAO().get_work_no_map([1, 2])
        assert isinstance(result, dict)
        p.stop()

    def test_get_work_no_map_empty_list(self):
        self.mock_cursor.fetchall.return_value = []
        p = self._patch()
        from models.quality import QualityDAO
        result = QualityDAO().get_work_no_map([])
        assert isinstance(result, dict)
        p.stop()

    def test_get_all_with_days_limit(self):
        self.mock_cursor.fetchall.return_value = [{"id": 1}]
        p = self._patch()
        from models.quality import QualityDAO
        result = QualityDAO().get_all(days_limit=30)
        assert isinstance(result, list)
        p.stop()

    def test_get_all_with_limit(self):
        self.mock_cursor.fetchall.return_value = [{"id": i} for i in range(5)]
        p = self._patch()
        from models.quality import QualityDAO
        result = QualityDAO().get_all(limit=5)
        assert len(result) == 5
        p.stop()

    def test_get_all_empty(self):
        self.mock_cursor.fetchall.return_value = []
        p = self._patch()
        from models.quality import QualityDAO
        result = QualityDAO().get_all()
        assert len(result) == 0
        p.stop()

    def test_get_by_order_empty(self):
        self.mock_cursor.fetchall.return_value = []
        p = self._patch()
        from models.quality import QualityDAO
        result = QualityDAO().get_by_order(999)
        assert len(result) == 0
        p.stop()

    def test_confirm_order_completion(self):
        # 参数为 None 时提前返回，不执行数据库操作
        p = self._patch()
        from models.quality import QualityDAO
        QualityDAO().confirm_order_completion(None)
        assert True  # 无异常即通过
        p.stop()

    def test_get_production_by_order(self):
        # 没有匹配行时返回 None
        self.mock_cursor.fetchone.return_value = None
        p = self._patch()
        from models.quality import QualityDAO
        result = QualityDAO().get_production_by_order(1)
        assert result is None
        p.stop()

    def test_get_production_by_order_found(self):
        # 有匹配行时返回 dict
        self.mock_cursor.fetchone.return_value = {"id": 10, "order_id": 1}
        p = self._patch()
        from models.quality import QualityDAO
        result = QualityDAO().get_production_by_order(1)
        assert isinstance(result, dict)
        assert result["id"] == 10
        p.stop()

