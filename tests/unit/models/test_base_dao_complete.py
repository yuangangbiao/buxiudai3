# -*- coding: utf-8 -*-
"""
models/base_dao.py 深度测试 - get_all/create/update/delete/count/exists/get_paginated/bulk_create/bulk_update
"""
import sys, os
import pytest
from unittest.mock import patch, MagicMock


class TestBaseDAOGetAll:
    """get_all() 方法测试"""

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        self.mock_cursor = MagicMock()
        self.mock_conn = MagicMock()
        # 正确设置 context manager
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

    def test_get_all_no_filters(self, dao):
        self.mock_cursor.fetchall.return_value = [{"id": 1}, {"id": 2}]
        result = dao.get_all()
        assert len(result) == 2

    def test_get_all_with_filters(self, dao):
        self.mock_cursor.fetchall.return_value = [{"id": 1, "name": "item1"}]
        result = dao.get_all(filters={"name": "item1", "status": "active"})
        assert len(result) == 1
        call_args = self.mock_cursor.execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]
        assert "AND name=%s" in sql
        assert "AND status=%s" in sql

    def test_get_all_with_none_filter_skipped(self, dao):
        self.mock_cursor.fetchall.return_value = []
        dao.get_all(filters={"name": "item1", "status": None})
        call_args = self.mock_cursor.execute.call_args
        sql = call_args[0][0]
        # None 值的过滤条件应被跳过
        assert "status=%s" not in sql

    def test_get_all_with_order_by(self, dao):
        self.mock_cursor.fetchall.return_value = []
        dao.get_all(order_by="created_at DESC")
        call_args = self.mock_cursor.execute.call_args
        sql = call_args[0][0]
        assert "ORDER BY created_at DESC" in sql

    def test_get_all_with_limit(self, dao):
        self.mock_cursor.fetchall.return_value = [{"id": 1}]
        dao.get_all(limit=10)
        call_args = self.mock_cursor.execute.call_args
        sql = call_args[0][0]
        assert "LIMIT 10" in sql

    def test_get_all_with_limit_and_offset(self, dao):
        self.mock_cursor.fetchall.return_value = [{"id": 11}]
        dao.get_all(limit=10, offset=10)
        call_args = self.mock_cursor.execute.call_args
        sql = call_args[0][0]
        assert "LIMIT 10" in sql
        assert "OFFSET 10" in sql


class TestBaseDAOCreate:
    """create() 方法测试 - ValueError 在 DB 调用前抛出"""

    @pytest.fixture
    def dao(self):
        from models.base_dao import BaseDAO
        return BaseDAO(table_name="test_table")

    def test_create_empty_data_raises(self, dao):
        with pytest.raises(ValueError, match="不能为空"):
            dao.create({})

    def test_create_only_id_fields_raises(self, dao):
        with pytest.raises(ValueError, match="没有有效的字段"):
            dao.create({"id": 1, "created_at": "2026-01-01", "updated_at": "2026-01-01"})

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

    def test_create_success(self, dao):
        self.mock_cursor.lastrowid = 42
        result = dao.create({"name": "item", "qty": 10})
        assert isinstance(result, int)


class TestBaseDAOUpdate:
    """update() 方法测试"""

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

    def test_update_empty_data_returns_false(self, dao):
        result = dao.update(1, {})
        assert result is False

    def test_update_only_id_field_returns_false(self, dao):
        result = dao.update(1, {"id": 999, "created_at": "2026-01-01"})
        assert result is False

    def test_update_rowcount_zero(self, dao):
        self.mock_cursor.rowcount = 0
        result = dao.update(1, {"name": "x"})
        assert result is False

    def test_update_success(self, dao):
        self.mock_cursor.rowcount = 1
        result = dao.update(1, {"name": "updated"})
        assert result is True


class TestBaseDAODelete:
    """delete() 方法测试"""

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

    def test_delete_soft(self, dao):
        self.mock_cursor.rowcount = 1
        result = dao.delete(1, hard=False)
        assert result is True
        call_args = self.mock_cursor.execute.call_args
        sql = call_args[0][0]
        assert "is_deleted=1" in sql

    def test_delete_hard(self, dao):
        self.mock_cursor.rowcount = 1
        result = dao.delete(1, hard=True)
        assert result is True
        call_args = self.mock_cursor.execute.call_args
        sql = call_args[0][0]
        assert "DELETE FROM" in sql


class TestBaseDAOExists:
    """exists() 方法测试"""

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

    def test_exists_true(self, dao):
        self.mock_cursor.fetchone.return_value = {"1": 1}
        assert dao.exists(id=1) is True

    def test_exists_false(self, dao):
        self.mock_cursor.fetchone.return_value = None
        assert dao.exists(id=9999) is False


class TestBaseDAOCount:
    """count() 方法测试"""

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

    def test_count_no_filters(self, dao):
        self.mock_cursor.fetchone.return_value = {"cnt": 42}
        assert dao.count() == 42

    def test_count_with_filters(self, dao):
        self.mock_cursor.fetchone.return_value = {"cnt": 5}
        dao.count(filters={"status": "active"})
        call_args = self.mock_cursor.execute.call_args
        sql = call_args[0][0]
        assert "AND status=%s" in sql


class TestBaseDAOGetPaginated:
    """get_paginated() 方法测试"""

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

    def test_get_paginated(self, dao):
        self.mock_cursor.fetchone.return_value = {"cnt": 55}  # count query
        self.mock_cursor.fetchall.return_value = [{"id": 1}]  # items query
        result = dao.get_paginated(page=2, page_size=10)
        assert "items" in result
        assert "total" in result
        assert result["page"] == 2
        assert result["page_size"] == 10

    def test_get_paginated_page_minimum_1(self, dao):
        self.mock_cursor.fetchone.return_value = {"cnt": 0}
        self.mock_cursor.fetchall.return_value = []
        result = dao.get_paginated(page=0)
        assert result["page"] == 1

    def test_get_paginated_page_size_max_100(self, dao):
        self.mock_cursor.fetchone.return_value = {"cnt": 0}
        self.mock_cursor.fetchall.return_value = []
        result = dao.get_paginated(page_size=200)
        assert result["page_size"] == 100


class TestBaseDAOBulkCreate:
    """bulk_create() 方法测试"""

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

    def test_bulk_create_empty_list(self, dao):
        result = dao.bulk_create([])
        assert result == 0

    def test_bulk_create_only_id_fields(self, dao):
        result = dao.bulk_create([{"id": 1, "created_at": "2026-01-01"}])
        assert result == 0

    def test_bulk_create_multiple_items(self, dao):
        result = dao.bulk_create([{"name": "a"}, {"name": "b"}, {"name": "c"}])
        assert result == 3


class TestBaseDAOBulkUpdate:
    """bulk_update() 方法测试"""

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

    def test_bulk_update_empty_ids(self, dao):
        result = dao.bulk_update([], {"name": "x"})
        assert result == 0

    def test_bulk_update_empty_data(self, dao):
        result = dao.bulk_update([1, 2, 3], {})
        assert result == 0

    def test_bulk_update_only_id_field(self, dao):
        result = dao.bulk_update([1, 2], {"id": 999, "created_at": "2026-01-01"})
        assert result == 0

    def test_bulk_update_success(self, dao):
        self.mock_cursor.rowcount = 2
        result = dao.bulk_update([1, 2], {"name": "updated"})
        assert result == 2
