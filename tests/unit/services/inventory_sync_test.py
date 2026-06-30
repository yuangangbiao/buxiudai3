# -*- coding: utf-8 -*-
"""Tests for services.inventory_sync — InventorySyncService."""

from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from services.inventory_sync import InventorySyncService


@pytest.fixture
def mock_dao():
    with patch("services.inventory_sync.InventoryDAO") as MockDAO:
        dao_instance = MagicMock()
        MockDAO.return_value = dao_instance
        yield dao_instance


class TestInventorySyncService:
    def test_init_creates_dao(self, mock_dao):
        svc = InventorySyncService()
        assert svc.dao is mock_dao

    def test_get_unified_stock(self, mock_dao):
        mock_dao.search_by_material.return_value = [
            {"material": "不锈钢网带", "qty": 100},
        ]
        svc = InventorySyncService()
        result = svc.get_unified_stock("不锈钢网带")
        assert result == [{"material": "不锈钢网带", "qty": 100}]
        mock_dao.search_by_material.assert_called_once_with("不锈钢网带")

    @patch("services.inventory_sync.pymysql")
    def test_check_duplicate_databases_returns_true(self, mock_pymysql):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [("stock",), ("orders",)]
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pymysql.connect.return_value = mock_conn

        svc = InventorySyncService()
        assert svc.check_duplicate_databases() is True
        mock_pymysql.connect.assert_called_once()

    @patch("services.inventory_sync.pymysql")
    def test_check_duplicate_databases_no_tables(self, mock_pymysql):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pymysql.connect.return_value = mock_conn

        svc = InventorySyncService()
        assert svc.check_duplicate_databases() is False

    @patch("services.inventory_sync.pymysql")
    def test_check_duplicate_databases_connection_fails(self, mock_pymysql):
        mock_pymysql.connect.side_effect = Exception("Connection refused")

        svc = InventorySyncService()
        assert svc.check_duplicate_databases() is False
