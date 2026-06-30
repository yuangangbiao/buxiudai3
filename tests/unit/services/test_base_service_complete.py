# -*- coding: utf-8 -*-
"""
services/base_service.py 完整单元测试

覆盖模块:
- BaseService
- transaction()
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest
from unittest.mock import patch, MagicMock


class TestBaseServiceExists:
    """BaseService 存在性测试"""

    def test_base_service_module_exists(self):
        """测试base_service模块存在"""
        from services import base_service
        assert base_service is not None

    def test_base_service_class_exists(self):
        """测试BaseService类存在"""
        from services.base_service import BaseService
        assert BaseService is not None


class TestBaseServiceInit:
    """BaseService 初始化测试"""

    def test_init_without_dao(self):
        """测试无DAO初始化"""
        from services.base_service import BaseService
        service = BaseService()
        assert service.dao is None

    def test_init_with_dao(self):
        """测试带DAO初始化"""
        from services.base_service import BaseService
        mock_dao = MagicMock()
        service = BaseService(dao=mock_dao)
        assert service.dao is mock_dao


class TestBaseServiceTransaction:
    """transaction 事务管理测试"""

    @patch('services.base_service.get_connection')
    def test_transaction_commit(self, mock_get_conn):
        """测试事务正常提交"""
        from services.base_service import BaseService

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        service = BaseService()

        with service.transaction() as conn:
            assert conn is mock_conn

        mock_conn.commit.assert_called_once()

    @patch('services.base_service.get_connection')
    def test_transaction_rollback_on_exception(self, mock_get_conn):
        """测试事务异常回滚"""
        from services.base_service import BaseService

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        service = BaseService()

        with pytest.raises(ValueError):
            with service.transaction() as conn:
                raise ValueError("Test error")

        mock_conn.rollback.assert_called_once()


class TestBaseServiceComplete:
    """BaseService 完整性测试"""

    def test_service_is_class(self):
        """测试BaseService是类"""
        from services.base_service import BaseService
        assert isinstance(BaseService, type)

    def test_service_has_transaction_method(self):
        """测试Service有transaction方法"""
        from services.base_service import BaseService
        service = BaseService()
        assert hasattr(service, 'transaction')
        assert callable(service.transaction)

    def test_service_has_dao_property(self):
        """测试Service有dao属性"""
        from services.base_service import BaseService
        service = BaseService()
        assert hasattr(service, 'dao')


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
