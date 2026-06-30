# -*- coding: utf-8 -*-
"""基础 DAO 层单元测试——直接mock替换"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock


class TestBaseDAO:
    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        self.mock_cursor = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_conn.cursor.return_value.__enter__.return_value = self.mock_cursor
        self.mock_conn.cursor.return_value.__exit__.return_value = None
        
        self.get_conn_patch = patch('models.base_dao.get_connection', return_value=self.mock_conn)
        self.get_conn_patch.start()
        yield
        self.get_conn_patch.stop()

    @pytest.fixture
    def dao(self):
        from models.base_dao import BaseDAO
        return BaseDAO(table_name="test_table")

    def test_get_by_id(self, dao):
        self.mock_cursor.fetchone.return_value = {"id": 1, "name": "test"}
        result = dao.get_by_id(1)
        assert result["id"] == 1

    def test_create_returns_int(self, dao):
        type(self.mock_cursor).lastrowid = PropertyMock(return_value=42)
        result = dao.create({"name": "item"})
        assert isinstance(result, int)

    def test_update_returns_bool(self, dao):
        type(self.mock_cursor).rowcount = PropertyMock(return_value=1)
        result = dao.update(1, {"name": "x"})
        assert isinstance(result, bool)

    def test_delete_returns_bool(self, dao):
        type(self.mock_cursor).rowcount = PropertyMock(return_value=1)
        result = dao.delete(1)
        assert isinstance(result, bool)

    def test_count_returns_int(self, dao):
        self.mock_cursor.fetchone.return_value = {"cnt": 5}
        result = dao.count()
        assert isinstance(result, int)
