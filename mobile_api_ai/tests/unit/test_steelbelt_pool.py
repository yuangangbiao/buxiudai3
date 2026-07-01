# -*- coding: utf-8 -*-
"""db/steelbelt_pool.py 单元测试"""
import pytest
from unittest.mock import patch, MagicMock


class TestSteelBeltPool:
    def test_get_conn_returns_connection(self):
        with patch('db.steelbelt_pool.PooledDB') as mock_pool:
            mock_conn = MagicMock()
            mock_pool.return_value.connection.return_value = mock_conn
            # force re-init
            import db.steelbelt_pool as sbp
            sbp._pool = None
            conn = sbp.get_conn()
            assert conn is mock_conn

    def test_cursor_returns_conn_and_cursor(self):
        with patch('db.steelbelt_pool.PooledDB') as mock_pool:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_pool.return_value.connection.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            import db.steelbelt_pool as sbp
            sbp._pool = None
            conn, cur = sbp.cursor()
            assert conn is mock_conn
            assert cur is mock_cursor

    def test_pool_is_singleton(self):
        with patch('db.steelbelt_pool.PooledDB') as mock_pool:
            import db.steelbelt_pool as sbp
            sbp._pool = None
            sbp.get_conn()
            sbp.get_conn()
            assert mock_pool.call_count == 1
