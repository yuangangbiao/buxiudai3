# -*- coding: utf-8 -*-
"""
models/operator.py 完整单元测试

覆盖模块:
- OperatorDAO
"""
import os
import sys
import pytest
from unittest.mock import Mock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestOperatorDAOExists:
    """OperatorDAO 存在性测试"""

    def test_operator_dao_class_exists(self):
        """测试OperatorDAO类存在"""
        from models.operator import OperatorDAO
        assert OperatorDAO is not None

    def test_operator_dao_has_get_all_method(self):
        """测试get_all方法存在"""
        from models.operator import OperatorDAO
        assert hasattr(OperatorDAO, 'get_all')

    def test_operator_dao_has_get_by_id_method(self):
        """测试get_by_id方法存在"""
        from models.operator import OperatorDAO
        assert hasattr(OperatorDAO, 'get_by_id')

    def test_operator_dao_has_get_by_wechat_method(self):
        """测试get_by_wechat_userid方法存在"""
        from models.operator import OperatorDAO
        assert hasattr(OperatorDAO, 'get_by_wechat_userid')


class TestOperatorDAOGetById:
    """OperatorDAO.get_by_id 测试"""

    @patch('models.operator.get_connection')
    def test_get_by_id_success(self, mock_get_conn):
        """测试根据ID获取操作员成功"""
        from models.operator import OperatorDAO

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            'id': 1,
            'operator_id': 'OP001',
            'name': '张三',
            'role': 'admin',
            'status': 'active'
        }

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        result = OperatorDAO.get_by_id('OP001')

        assert result is not None
        assert result['operator_id'] == 'OP001'
        assert result['name'] == '张三'

    @patch('models.operator.get_connection')
    def test_get_by_id_not_found(self, mock_get_conn):
        """测试操作员不存在"""
        from models.operator import OperatorDAO

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        result = OperatorDAO.get_by_id('NONEXISTENT')

        assert result is None


class TestOperatorDAOGetAll:
    """OperatorDAO.get_all 测试"""

    @patch('models.operator.get_connection')
    def test_get_all_returns_list(self, mock_get_conn):
        """测试获取所有操作员"""
        from models.operator import OperatorDAO

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {'id': 1, 'operator_id': 'OP001', 'name': '张三', 'role': 'admin'},
            {'id': 2, 'operator_id': 'OP002', 'name': '李四', 'role': 'user'}
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        result = OperatorDAO.get_all()

        assert isinstance(result, list)
        assert len(result) == 2

    @patch('models.operator.get_connection')
    def test_get_all_empty(self, mock_get_conn):
        """测试没有操作员"""
        from models.operator import OperatorDAO

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        result = OperatorDAO.get_all()

        assert isinstance(result, list)
        assert len(result) == 0


class TestOperatorDAOGetByWechat:
    """OperatorDAO.get_by_wechat_userid 测试"""

    @patch('models.operator.get_connection')
    def test_get_by_wechat_success(self, mock_get_conn):
        """测试根据企业微信ID获取操作员成功"""
        from models.operator import OperatorDAO

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            'id': 1,
            'operator_id': 'OP001',
            'name': '张三',
            'wechat_userid': 'wx123456'
        }

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        result = OperatorDAO.get_by_wechat_userid('wx123456')

        assert result is not None
        assert result['wechat_userid'] == 'wx123456'

    @patch('models.operator.get_connection')
    def test_get_by_wechat_not_found(self, mock_get_conn):
        """测试企业微信ID不存在"""
        from models.operator import OperatorDAO

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        result = OperatorDAO.get_by_wechat_userid('nonexistent')

        assert result is None

    @patch('models.operator.get_connection')
    def test_get_by_wechat_empty_string(self, mock_get_conn):
        """测试空字符串返回None"""
        from models.operator import OperatorDAO

        result = OperatorDAO.get_by_wechat_userid('')

        assert result is None
        mock_get_conn.assert_not_called()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
