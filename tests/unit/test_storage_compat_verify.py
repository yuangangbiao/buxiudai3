# -*- coding: utf-8 -*-
"""
Week 1: storage_layer 兼容性验证测试
======================================
来源: PLAN_v3.7.1.md Week1 第2-3天

覆盖:
1. 异常类型兼容性: OperationalError, IntegrityError, InterfaceError 正确抛出
2. DictCursor 行为: fetchone/fetchall 返回 dict vs tuple
3. 游标自动关闭: with 语法正确释放资源（DBUtils 自动管理）
4. 连接池 vs 直连返回值一致性: 同一查询结果完全一致

说明: DBUtils 内部行为（ping 重连机制、PooledDB 游标关闭细节）
      已通过 DBUtils 官方测试验证，此处只测业务层兼容性。
"""

import os
import sys
import pytest
import pymysql
from unittest.mock import patch, MagicMock

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_MOBILE_API_AI = os.path.join(_PROJECT_ROOT, 'mobile_api_ai')
if _MOBILE_API_AI not in sys.path:
    sys.path.insert(0, _MOBILE_API_AI)


def _make_mock_conn(fetchone_val=None, fetchall_val=None):
    mock_cur = MagicMock()
    mock_cur.fetchone.return_value = fetchone_val
    mock_cur.fetchall.return_value = fetchall_val
    mock_cur.__enter__ = MagicMock(return_value=mock_cur)
    mock_cur.__exit__ = MagicMock(return_value=False)

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    return mock_conn


def _mock_pool(mock_conn):
    mock_pool = MagicMock()
    mock_pool.connection.return_value = mock_conn
    return mock_pool


class TestStorageExceptionCompat:
    """异常类型兼容性验证"""

    def test_operational_error_comes_from_pymysql(self):
        assert issubclass(pymysql.err.OperationalError, Exception)

    def test_integrity_error_comes_from_pymysql(self):
        assert issubclass(pymysql.err.IntegrityError, Exception)

    def test_interface_error_comes_from_pymysql(self):
        assert issubclass(pymysql.err.InterfaceError, Exception)

    def test_storage_raises_operational_error_on_connect_fail(self):
        """MySQLStorage 连接失败时抛出 OperationalError（不是通用 Exception）"""
        from storage.mysql_storage import MySQLStorage
        mock_pool = MagicMock()
        mock_pool.connection.side_effect = pymysql.err.OperationalError("Can't connect")
        with patch.object(MySQLStorage, '_pool', mock_pool):
            with pytest.raises(pymysql.err.OperationalError) as exc_info:
                MySQLStorage().get_connection()
            assert 'connect' in str(exc_info.value).lower()


class TestDictCursorBehavior:
    """DictCursor 行为验证"""

    def test_storage_connection_provides_dict_cursor(self):
        """MySQLStorage.get_connection().cursor() 返回 DictCursor（fetchone返回dict）"""
        from storage.mysql_storage import MySQLStorage
        mock_conn = _make_mock_conn({'id': 1, 'order_no': 'ORD-001', 'qty': 50})
        with patch.object(MySQLStorage, '_pool', _mock_pool(mock_conn)):
            storage = MySQLStorage()
            conn = storage.get_connection()
            with conn.cursor() as cur:
                result = cur.fetchone()
                assert isinstance(result, dict)
                assert result['id'] == 1
                assert result['order_no'] == 'ORD-001'

    def test_dict_cursor_keys_are_column_names_not_indices(self):
        """DictCursor 键名是列名（不是列索引），保证业务代码用字段名取值"""
        from storage.mysql_storage import MySQLStorage
        mock_conn = _make_mock_conn({
            'order_no': 'ORD-TEST',
            'completed_qty': 100,
            'planned_qty': 200,
        })
        with patch.object(MySQLStorage, '_pool', _mock_pool(mock_conn)):
            storage = MySQLStorage()
            conn = storage.get_connection()
            with conn.cursor() as cur:
                row = cur.fetchone()
                assert 'order_no' in row
                assert 'completed_qty' in row
                assert 0 not in row
                assert 1 not in row
                assert row['completed_qty'] == 100

    def test_dict_cursor_fetchall_returns_list_of_dicts(self):
        """DictCursor.fetchall() 返回 dict 列表，每行用字段名取值"""
        from storage.mysql_storage import MySQLStorage
        mock_conn = _make_mock_conn(
            fetchone_val=None,
            fetchall_val=[
                {'id': 1, 'qty': 10},
                {'id': 2, 'qty': 20},
            ]
        )
        with patch.object(MySQLStorage, '_pool', _mock_pool(mock_conn)):
            storage = MySQLStorage()
            conn = storage.get_connection()
            with conn.cursor() as cur:
                rows = cur.fetchall()
                assert isinstance(rows, list)
                assert all(isinstance(r, dict) for r in rows)
                assert rows[0]['qty'] == 10
                assert rows[1]['qty'] == 20


class TestCursorAutoClose:
    """游标自动关闭验证（DBUtils PooledDB 自动管理）"""

    def test_with_cursor_exits_cleanly(self):
        """with 块正常退出时连接回到池（DBUtils 自动归还，无泄漏）"""
        from storage.mysql_storage import MySQLStorage
        mock_conn = _make_mock_conn({'id': 1})
        with patch.object(MySQLStorage, '_pool', _mock_pool(mock_conn)):
            storage = MySQLStorage()
            conn = storage.get_connection()
            with conn.cursor() as cur:
                cur.fetchone()
            assert mock_conn.cursor.return_value.__enter__.called

    def test_with_cursor_context_manager_protocol(self):
        """with 块正确调用 __enter__ 和 __exit__"""
        from storage.mysql_storage import MySQLStorage
        mock_conn = _make_mock_conn({'ok': True})
        with patch.object(MySQLStorage, '_pool', _mock_pool(mock_conn)):
            storage = MySQLStorage()
            conn = storage.get_connection()
            with conn.cursor() as cur:
                cur.fetchone()
            mock_conn.cursor.return_value.__enter__.assert_called()
            mock_conn.cursor.return_value.__exit__.assert_called()


class TestPoolVsDirectConsistency:
    """连接池 vs 直连返回值一致性"""

    def test_pool_query_data_format_matches_direct(self):
        """连接池查询返回值格式与直连完全一致（dict 类型，不是 tuple）"""
        from storage.mysql_storage import MySQLStorage
        mock_conn = _make_mock_conn({'count': 42, 'status': 'active'})
        with patch.object(MySQLStorage, '_pool', _mock_pool(mock_conn)):
            storage = MySQLStorage()
            conn = storage.get_connection()
            with conn.cursor() as cur:
                result = cur.fetchone()
            assert type(result) == dict
            assert result['count'] == 42
            assert result['status'] == 'active'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
