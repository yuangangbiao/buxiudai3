# -*- coding: utf-8 -*-
"""
utils/auto_schema.py 增量测试 — 目标模块覆盖率 80%+

覆盖未覆盖行: 60, 66-69, 71-74, 84, 92-93, 100-114, 118-133,
139-140, 146-147, 168, 172, 179-180, 196, 201-204, 208, 220,
227-230, 235, 241-242, 249-279, 300-311, 314-324, 327, 330, 333, 336
"""
import sys
import pytest
from unittest.mock import MagicMock, patch, PropertyMock


# ============================================================
#  _infer_sql_type 增量
# ============================================================

class TestInferSqlType:
    def test_bool_sqlite(self):
        from utils.auto_schema import _infer_sql_type
        assert _infer_sql_type(True, True) == 'INTEGER'

    def test_bool_mysql(self):
        from utils.auto_schema import _infer_sql_type
        assert _infer_sql_type(False, False) == 'TINYINT(1)'


# ============================================================
#  _get_db_identity
# ============================================================

class TestGetDbIdentity:
    def test_pymysql_with_db(self):
        from utils.auto_schema import _get_db_identity
        mock_conn = MagicMock()
        mock_conn.db = 'test_db'
        with patch.object(type(mock_conn), '__module__', 'pymysql.connections'):
            result = _get_db_identity(mock_conn)
        assert result == 'mysql:test_db'

    def test_pymysql_no_db(self):
        from utils.auto_schema import _get_db_identity
        mock_conn = MagicMock()
        del mock_conn.db
        with patch.object(type(mock_conn), '__module__', 'pymysql.connections'):
            result = _get_db_identity(mock_conn)
        assert result.startswith('mysql:')

    def test_sqlite_with_database(self):
        from utils.auto_schema import _get_db_identity
        mock_conn = MagicMock()
        mock_conn.database = '/tmp/test.db'
        with patch.object(type(mock_conn), '__module__', 'sqlite3.dbapi2'):
            result = _get_db_identity(mock_conn)
        assert result == 'sqlite:/tmp/test.db'

    def test_sqlite_no_database(self):
        from utils.auto_schema import _get_db_identity
        mock_conn = MagicMock()
        del mock_conn.database
        with patch.object(type(mock_conn), '__module__', 'sqlite3.dbapi2'):
            result = _get_db_identity(mock_conn)
        assert result.startswith('sqlite:')

    def test_unknown_module(self):
        from utils.auto_schema import _get_db_identity
        mock_conn = MagicMock()
        with patch.object(type(mock_conn), '__module__', 'some.other.driver'):
            result = _get_db_identity(mock_conn)
        assert result.startswith('unknown:')


# ============================================================
#  _validate_name
# ============================================================

class TestValidateName:
    def test_valid_name(self):
        from utils.auto_schema import _validate_name
        assert _validate_name('orders') is True
        assert _validate_name('order_items') is True
        assert _validate_name('_tmp_table') is True

    def test_invalid_name(self):
        from utils.auto_schema import _validate_name
        assert _validate_name('123table') is False
        assert _validate_name('table name') is False
        assert _validate_name('table-name') is False
        assert _validate_name('') is False


# ============================================================
#  _check_table_exists
# ============================================================

class TestCheckTableExists:
    def test_sqlite_table_exists(self):
        from utils.auto_schema import _check_table_exists
        cursor = MagicMock()
        cursor.fetchone.return_value = ('orders',)
        assert _check_table_exists(cursor, 'orders', True) is True
        args = cursor.execute.call_args[0]
        assert 'sqlite_master' in args[0]

    def test_mysql_table_exists(self):
        from utils.auto_schema import _check_table_exists
        cursor = MagicMock()
        cursor.fetchone.return_value = ('orders',)
        assert _check_table_exists(cursor, 'orders', False) is True
        args = cursor.execute.call_args[0]
        assert 'SHOW TABLES' in args[0]

    def test_table_not_exists(self):
        from utils.auto_schema import _check_table_exists
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        assert _check_table_exists(cursor, 'nope', False) is False


# ============================================================
#  _get_existing_columns
# ============================================================

class TestGetExistingColumns:
    def test_sqlite(self):
        from utils.auto_schema import _get_existing_columns
        cursor = MagicMock()
        cursor.fetchall.return_value = [(0, 'id', 'INTEGER', 0, None, 1), (1, 'name', 'TEXT', 0, None, 0)]
        result = _get_existing_columns(cursor, 'orders', True)
        assert result == {'id', 'name'}

    def test_mysql(self):
        from utils.auto_schema import _get_existing_columns
        cursor = MagicMock()
        cursor.fetchall.return_value = [{'Field': 'id'}, {'Field': 'name'}]
        result = _get_existing_columns(cursor, 'orders', False)
        assert result == {'id', 'name'}


# ============================================================
#  _create_table_ddl
# ============================================================

class TestCreateTableDdl:
    def test_create_table_success(self):
        from utils.auto_schema import _create_table_ddl
        conn = MagicMock()
        _create_table_ddl(conn, 'test_table', {'name': 'VARCHAR(255)', 'qty': 'INT'}, False)
        assert conn.cursor.return_value.execute.called
        conn.commit.assert_called_once()
        conn.cursor.return_value.close.assert_called_once()

    def test_create_table_failure(self):
        from utils.auto_schema import _create_table_ddl
        conn = MagicMock()
        conn.cursor.return_value.execute.side_effect = Exception('Table already exists')
        _create_table_ddl(conn, 'test_table', {'name': 'TEXT'}, True)
        conn.rollback.assert_called_once()

    def test_create_table_sqlite(self):
        from utils.auto_schema import _create_table_ddl
        conn = MagicMock()
        _create_table_ddl(conn, 'test_table', {'name': 'TEXT'}, True)
        sql = conn.cursor.return_value.execute.call_args[0][0]
        assert 'ENGINE=InnoDB' not in sql


# ============================================================
#  _add_missing_columns_ddl
# ============================================================

class TestAddMissingColumnsDdl:
    def test_add_all_success(self):
        from utils.auto_schema import _add_missing_columns_ddl
        conn = MagicMock()
        _add_missing_columns_ddl(conn, 'test_table', {'col1': 'INT', 'col2': 'TEXT'}, False)
        assert conn.cursor.return_value.execute.call_count == 2
        conn.commit.assert_called_once()
        conn.cursor.return_value.close.assert_called_once()

    def test_one_column_fails_others_succeed(self):
        from utils.auto_schema import _add_missing_columns_ddl
        conn = MagicMock()
        mock_cursor = MagicMock()
        conn.cursor.return_value = mock_cursor
        # 第一列失败，第二列成功
        mock_cursor.execute.side_effect = [Exception('Duplicate column'), None]
        _add_missing_columns_ddl(conn, 'test_table', {'col1': 'INT', 'col2': 'TEXT'}, False)
        conn.commit.assert_called_once()

    def test_no_columns_empty(self):
        from utils.auto_schema import _add_missing_columns_ddl
        conn = MagicMock()
        _add_missing_columns_ddl(conn, 'test_table', {}, False)
        conn.commit.assert_not_called()


# ============================================================
#  _open_ddl_connection
# ============================================================

class TestOpenDdlConnection:
    def test_pymysql(self):
        from utils.auto_schema import _open_ddl_connection
        mock_conn = MagicMock()
        mock_conn.host = 'localhost'
        mock_conn.port = 3306
        mock_conn.user = 'root'
        mock_conn.password = ''
        mock_conn.db = 'test'
        mock_ddl_conn = MagicMock()
        with patch.object(type(mock_conn), '__module__', 'pymysql.connections'):
            with patch('core.db.get_direct_connection', return_value=mock_ddl_conn) as mock_gdc:
                result = _open_ddl_connection(mock_conn)
                assert result == mock_ddl_conn
                mock_gdc.assert_called_once_with(
                    host='localhost', port=3306,
                    user='root', password='',
                    database='test', charset='utf8mb4',
                )

    def test_sqlite3(self):
        from utils.auto_schema import _open_ddl_connection
        mock_conn = MagicMock()
        mock_conn.database = '/tmp/test.db'
        mock_sqlite3 = MagicMock()
        mock_ddl_conn = MagicMock()
        mock_sqlite3.connect.return_value = mock_ddl_conn
        with patch.object(type(mock_conn), '__module__', 'sqlite3.dbapi2'):
            with patch.dict('sys.modules', {'sqlite3': mock_sqlite3}, clear=False):
                result = _open_ddl_connection(mock_conn)
                assert result == mock_ddl_conn
                mock_sqlite3.connect.assert_called_once_with('/tmp/test.db', timeout=10)

    def test_unknown(self):
        from utils.auto_schema import _open_ddl_connection
        mock_conn = MagicMock()
        with patch.object(type(mock_conn), '__module__', 'some.driver'):
            result = _open_ddl_connection(mock_conn)
        assert result is None


# ============================================================
#  auto_ensure_schema — 核心入口函数
# ============================================================

class TestAutoEnsureSchema:
    def test_empty_data_returns_early(self):
        from utils.auto_schema import auto_ensure_schema
        conn = MagicMock()
        # 空 data -> return
        auto_ensure_schema(conn, 'orders', {})
        assert conn.cursor.called is False

    def test_empty_table_name_returns_early(self):
        from utils.auto_schema import auto_ensure_schema
        conn = MagicMock()
        auto_ensure_schema(conn, '', {'name': 'x'})
        assert conn.cursor.called is False

    def test_invalid_table_name(self):
        from utils.auto_schema import auto_ensure_schema
        conn = MagicMock()
        auto_ensure_schema(conn, '123bad_name', {'name': 'x'})
        assert conn.cursor.called is False

    def test_cached_returns_early(self):
        from utils.auto_schema import auto_ensure_schema, _schema_cache, _schema_lock
        mock_conn = MagicMock()
        mock_conn.db = 'test'
        cache_key = 'mysql:test:orders'
        with _schema_lock:
            _schema_cache[cache_key] = True
        try:
            with patch.object(type(mock_conn), '__module__', 'pymysql.connections'):
                auto_ensure_schema(mock_conn, 'orders', {'name': 'x'})
            # 光标不应被创建
            assert mock_conn.cursor.called is False
        finally:
            with _schema_lock:
                _schema_cache.pop(cache_key, None)

    def test_create_new_table(self):
        from utils.auto_schema import auto_ensure_schema
        # 模拟 pymysql 连接，表不存在
        mock_conn = MagicMock()
        mock_conn.db = 'test'
        mock_conn.host = 'localhost'
        mock_conn.port = 3306
        mock_conn.user = 'root'
        mock_conn.password = ''
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None  # 表不存在
        mock_conn.cursor.return_value = mock_cursor

        with patch.object(type(mock_conn), '__module__', 'pymysql.connections'):
            with patch('utils.auto_schema._root_module._open_ddl_connection') as mock_open:
                mock_ddl_conn = MagicMock()
                mock_open.return_value = mock_ddl_conn
                auto_ensure_schema(mock_conn, 'new_table', {'name': 'test', 'qty': 100})

        # 建表 DDL 被调用
        mock_ddl_conn.cursor.return_value.execute.assert_called()
        mock_ddl_conn.close.assert_called_once()

    def test_add_missing_columns(self):
        from utils.auto_schema import auto_ensure_schema, _schema_cache, _schema_lock
        mock_conn = MagicMock()
        mock_conn.db = 'test'
        mock_conn.host = 'localhost'
        mock_conn.port = 3306
        mock_conn.user = 'root'
        mock_conn.password = ''
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ('orders',)  # 表存在
        mock_cursor.fetchall.return_value = [{'Field': 'id'}, {'Field': 'name'}]  # 已有列
        mock_conn.cursor.return_value = mock_cursor

        # 清除缓存确保走完整路径
        cache_key = 'mysql:test:orders'
        with _schema_lock:
            _schema_cache.pop(cache_key, None)

        with patch.object(type(mock_conn), '__module__', 'pymysql.connections'):
            with patch('utils.auto_schema._root_module._open_ddl_connection') as mock_open:
                mock_ddl_conn = MagicMock()
                mock_open.return_value = mock_ddl_conn
                auto_ensure_schema(mock_conn, 'orders', {'name': 'x', 'qty': 10, 'note': 'hi'})

        # 'qty' 和 'note' 不在已有列中，应该触发 DDL
        assert mock_open.called
        mock_ddl_conn.close.assert_called_once()

    def test_table_exists_no_missing_columns(self):
        """表存在且全部列已存在 -> 只缓存，不触发 DDL"""
        from utils.auto_schema import auto_ensure_schema, _schema_cache, _schema_lock
        mock_conn = MagicMock()
        mock_conn.db = 'test'
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ('orders',)  # 表存在
        mock_cursor.fetchall.return_value = [{'Field': 'id'}, {'Field': 'name'}, {'Field': 'qty'}]
        mock_conn.cursor.return_value = mock_cursor

        cache_key = 'mysql:test:orders'
        with _schema_lock:
            _schema_cache.pop(cache_key, None)

        with patch.object(type(mock_conn), '__module__', 'pymysql.connections'):
            with patch('utils.auto_schema._root_module._open_ddl_connection') as mock_open:
                auto_ensure_schema(mock_conn, 'orders', {'name': 'x', 'qty': 10})
        # 不应该调用 open_ddl_connection
        mock_open.assert_not_called()


# ============================================================
#  clear_schema_cache
# ============================================================

class TestClearSchemaCache:
    def test_clear_cache(self):
        from utils.auto_schema import clear_schema_cache, _schema_cache, _schema_lock
        with _schema_lock:
            _schema_cache['k1'] = True
            _schema_cache['k2'] = True
        clear_schema_cache()
        with _schema_lock:
            assert len(_schema_cache) == 0


# ============================================================
#  _build_data_from_sql
# ============================================================

class TestBuildDataFromSql:
    def test_insert_full(self):
        from utils.auto_schema import _build_data_from_sql
        sql = "INSERT INTO orders (name, qty) VALUES (%s, %s)"
        result = _build_data_from_sql(sql, ('test', 10))
        assert result is not None
        table, data = result
        assert table == 'orders'
        assert data == {'name': 'test', 'qty': 10}

    def test_insert_on_duplicate_key(self):
        from utils.auto_schema import _build_data_from_sql
        sql = "INSERT INTO orders (name, qty) VALUES (%s, %s) ON DUPLICATE KEY UPDATE qty=qty+1"
        result = _build_data_from_sql(sql, ('test', 10))
        assert result is not None
        table, data = result
        assert table == 'orders'
        # ON DUPLICATE 后缀被裁剪，只提取 VALUES 中的参数
        assert len(data) == 2

    def test_update_basic(self):
        from utils.auto_schema import _build_data_from_sql
        sql = "UPDATE orders SET name=%s, qty=%s WHERE id=%s"
        result = _build_data_from_sql(sql, ('new_name', 20, 1))
        assert result is not None
        table, data = result
        assert table == 'orders'
        assert data == {'name': 'new_name', 'qty': 20}

    def test_update_no_where(self):
        from utils.auto_schema import _build_data_from_sql
        sql = "UPDATE orders SET name=%s, qty=%s"
        result = _build_data_from_sql(sql, ('x', 5))
        assert result is not None
        assert 'name' in result[1]

    def test_invalid_sql_returns_none(self):
        from utils.auto_schema import _build_data_from_sql
        sql = "SELECT * FROM orders"
        result = _build_data_from_sql(sql, None)
        assert result is None

    def test_insert_params_not_list(self):
        from utils.auto_schema import _build_data_from_sql
        sql = "INSERT INTO orders (name) VALUES (%s)"
        result = _build_data_from_sql(sql, None)
        assert result is None

    def test_insert_with_invalid_col_name(self):
        from utils.auto_schema import _build_data_from_sql
        sql = "INSERT INTO t (123col) VALUES (%s)"
        result = _build_data_from_sql(sql, ('x',))
        assert result is None


# ============================================================
#  SafeCursor
# ============================================================

class TestSafeCursor:
    def test_execute_with_params(self):
        from utils.auto_schema import SafeCursor
        cursor = MagicMock()
        conn = MagicMock()
        with patch.object(type(conn), '__module__', 'sqlite3.dbapi2'):
            sc = SafeCursor(cursor, conn)
            sc.execute("INSERT INTO t (name) VALUES (?)", ('hello',))
        cursor.execute.assert_called_once_with("INSERT INTO t (name) VALUES (?)", ('hello',))

    def test_execute_without_params(self):
        from utils.auto_schema import SafeCursor
        cursor = MagicMock()
        conn = MagicMock()
        with patch.object(type(conn), '__module__', 'sqlite3.dbapi2'):
            sc = SafeCursor(cursor, conn)
            sc.execute("SELECT 1")
        cursor.execute.assert_called_once_with("SELECT 1")

    def test_execute_pymysql_convert_placeholder(self):
        from utils.auto_schema import SafeCursor
        cursor = MagicMock()
        conn = MagicMock()
        with patch.object(type(conn), '__module__', 'pymysql.connections'):
            sc = SafeCursor(cursor, conn)
            sc.execute("INSERT INTO t (name) VALUES (?)", ('hello',))
        # pymysql 下 ? 被转换成 %s
        called_sql = cursor.execute.call_args[0][0]
        assert '%s' in called_sql
        assert '?' not in called_sql

    def test_executemany(self):
        from utils.auto_schema import SafeCursor
        cursor = MagicMock()
        conn = MagicMock()
        with patch.object(type(conn), '__module__', 'sqlite3.dbapi2'):
            sc = SafeCursor(cursor, conn)
            sc.executemany("INSERT INTO t (name) VALUES (?)", [('a',), ('b',)])
        cursor.executemany.assert_called_once()

    def test_executemany_pymysql(self):
        from utils.auto_schema import SafeCursor
        cursor = MagicMock()
        conn = MagicMock()
        with patch.object(type(conn), '__module__', 'pymysql.connections'):
            sc = SafeCursor(cursor, conn)
            sc.executemany("INSERT INTO t (name) VALUES (?)", [('a',)])
        called_sql = cursor.executemany.call_args[0][0]
        assert '%s' in called_sql

    def test_executemany_empty_seq(self):
        from utils.auto_schema import SafeCursor
        cursor = MagicMock()
        conn = MagicMock()
        with patch.object(type(conn), '__module__', 'sqlite3.dbapi2'):
            sc = SafeCursor(cursor, conn)
            sc.executemany("INSERT INTO t (name) VALUES (?)", [])
        # 空序列不应该触发 auto_ensure_schema 但应该透传
        cursor.executemany.assert_called_once()

    def test_iter(self):
        from utils.auto_schema import SafeCursor
        cursor = MagicMock()
        cursor.__iter__.return_value = iter([1, 2, 3])
        sc = SafeCursor(cursor, None)
        assert list(sc) == [1, 2, 3]

    def test_enter_exit(self):
        from utils.auto_schema import SafeCursor
        cursor = MagicMock()
        cursor.__exit__.return_value = None
        conn = MagicMock()
        sc = SafeCursor(cursor, conn)
        with sc as s:
            assert s is sc
        # SafeCursor.__enter__ 直接返回 self，不委托给 cursor
        # SafeCursor.__exit__ 委托给 self._cursor.__exit__
        cursor.__exit__.assert_called_once()

    def test_getattr_delegates(self):
        from utils.auto_schema import SafeCursor
        cursor = MagicMock()
        cursor.fetchone.return_value = (42,)
        sc = SafeCursor(cursor, None)
        result = sc.fetchone()
        assert result == (42,)
