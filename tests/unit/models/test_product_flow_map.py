# Phase 1: 覆盖 0% 模块 — product_flow_map.py 单元测试
import pytest
from unittest.mock import patch, MagicMock
from models.product_flow_map import ProductFlowMapDAO


class TestProductFlowMapDAO:
    """ProductFlowMapDAO.get_flow_type() 单元测试"""

    # ---------- 正常路径 ----------

    def test_get_flow_type_returns_dict_flow_type(self):
        """数据库返回 dict 时返回 flow_type 字段值"""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {'flow_type': 'custom'}
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch('models.product_flow_map.get_connection', return_value=mock_conn):
            result = ProductFlowMapDAO.get_flow_type(42)

        assert result == 'custom'
        mock_cursor.execute.assert_called_once_with(
            "SELECT flow_type FROM product_flow_map WHERE product_type_id=%s", (42,)
        )
        mock_conn.close.assert_called_once()

    def test_get_flow_type_returns_tuple_flow_type(self):
        """数据库返回 tuple 时取第一个元素"""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ('custom',)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch('models.product_flow_map.get_connection', return_value=mock_conn):
            result = ProductFlowMapDAO.get_flow_type(99)

        assert result == 'custom'

    def test_get_flow_type_not_found_returns_default(self):
        """未找到记录时返回默认值 'production'"""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch('models.product_flow_map.get_connection', return_value=mock_conn):
            result = ProductFlowMapDAO.get_flow_type(999)

        assert result == 'production'

    def test_get_flow_type_dict_missing_key_returns_default(self):
        """dict 中缺少 flow_type 键时返回默认值 'production'"""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {'other_field': 'val'}
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch('models.product_flow_map.get_connection', return_value=mock_conn):
            result = ProductFlowMapDAO.get_flow_type(1)

        assert result == 'production'

    # ---------- 异常路径 ----------

    def test_get_flow_type_db_error(self):
        """数据库异常时向上传播"""
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception('DB connection lost')
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch('models.product_flow_map.get_connection', return_value=mock_conn):
            with pytest.raises(Exception, match='DB connection lost'):
                ProductFlowMapDAO.get_flow_type(1)

        mock_conn.close.assert_called_once()
