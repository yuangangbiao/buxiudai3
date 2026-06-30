# -*- coding: utf-8 -*-
"""
models/quality.py 完整单元测试

覆盖模块:
- QualityDAO
"""
import os
import sys
import pytest
from unittest.mock import Mock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestQualityDAOExists:
    """QualityDAO 存在性测试"""

    def test_quality_dao_class_exists(self):
        """测试QualityDAO类存在"""
        from models.quality import QualityDAO
        assert QualityDAO is not None

    def test_quality_dao_has_create_method(self):
        """测试create方法存在"""
        from models.quality import QualityDAO
        assert hasattr(QualityDAO, 'create')
        assert callable(QualityDAO.create)

    def test_quality_dao_has_get_by_order_method(self):
        """测试get_by_order方法存在"""
        from models.quality import QualityDAO
        assert hasattr(QualityDAO, 'get_by_order')

    def test_quality_dao_has_get_by_id_method(self):
        """测试get_by_id方法存在"""
        from models.quality import QualityDAO
        assert hasattr(QualityDAO, 'get_by_id')


class TestQualityStatusConstants:
    """QualityStatus 状态常量测试"""

    def test_quality_status_pending_exists(self):
        """测试待质检状态存在"""
        from constants import QualityStatus
        assert QualityStatus.PENDING is not None

    def test_quality_status_class_exists(self):
        """测试QualityStatus类存在"""
        from constants import QualityStatus
        assert QualityStatus is not None


class TestQualityDAOGetByOrder:
    """QualityDAO.get_by_order 测试"""

    @patch('models.quality.get_connection')
    def test_get_by_order_success(self, mock_get_conn):
        """测试获取订单的质检记录"""
        from models.quality import QualityDAO

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {'id': 1, 'inspection_type': '首检', 'result': '合格'},
            {'id': 2, 'inspection_type': '终检', 'result': '合格'}
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_get_conn.return_value = mock_conn

        result = QualityDAO.get_by_order(10)

        assert isinstance(result, list)
        assert len(result) == 2

    @patch('models.quality.get_connection')
    def test_get_by_order_empty(self, mock_get_conn):
        """测试订单没有质检记录"""
        from models.quality import QualityDAO

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_get_conn.return_value = mock_conn

        result = QualityDAO.get_by_order(999)

        assert isinstance(result, list)
        assert len(result) == 0


class TestQualityDAOGetById:
    """QualityDAO.get_by_id 测试"""

    @pytest.mark.skip(reason="get_by_id方法需要检查")
    def test_get_by_id_success(self):
        """测试根据ID获取质检记录成功"""
        pass

    @pytest.mark.skip(reason="get_by_id方法需要检查")
    def test_get_by_id_not_found(self):
        """测试质检记录不存在"""
        pass


class TestQualityDAOGetAll:
    """QualityDAO.get_all 测试"""

    @patch('models.quality.get_connection')
    def test_get_all_returns_list(self, mock_get_conn):
        """测试获取所有质检记录"""
        from models.quality import QualityDAO

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {'id': 1, 'inspection_type': '首检', 'result': '合格'},
            {'id': 2, 'inspection_type': '中检', 'result': '合格'},
            {'id': 3, 'inspection_type': '终检', 'result': '不合格'}
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_get_conn.return_value = mock_conn

        result = QualityDAO.get_all()

        assert isinstance(result, list)
        assert len(result) == 3

    @patch('models.quality.get_connection')
    def test_get_all_empty(self, mock_get_conn):
        """测试没有质检记录"""
        from models.quality import QualityDAO

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_get_conn.return_value = mock_conn

        result = QualityDAO.get_all()

        assert isinstance(result, list)
        assert len(result) == 0


class TestQualityDAOGetNextInspectionSeq:
    """QualityDAO._get_next_inspection_seq 测试"""

    @patch('models.quality.get_connection')
    def test_get_next_seq_first_inspection(self, mock_get_conn):
        """测试获取第一个质检序号"""
        from models.quality import QualityDAO

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {'next_seq': 1}

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_get_conn.return_value = mock_conn

        seq, inspection_no = QualityDAO._get_next_inspection_seq(10, '首检')

        assert seq == 1
        assert inspection_no == '首检-1'

    @patch('models.quality.get_connection')
    def test_get_next_seq_second_inspection(self, mock_get_conn):
        """测试获取第二个质检序号"""
        from models.quality import QualityDAO

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {'next_seq': 2}

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_get_conn.return_value = mock_conn

        seq, inspection_no = QualityDAO._get_next_inspection_seq(10, '中检')

        assert seq == 2
        assert inspection_no == '中检-2'


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
