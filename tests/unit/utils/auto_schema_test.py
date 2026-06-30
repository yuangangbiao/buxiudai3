# -*- coding: utf-8 -*-
"""Tests for utils.auto_schema — Auto schema, SafeCursor."""

import re
from unittest.mock import MagicMock, patch, PropertyMock, call

import pytest

from utils.auto_schema import (
    _infer_sql_type,
    _get_db_identity,
    _validate_name,
    _check_table_exists,
    _get_existing_columns,
    _create_table_ddl,
    _add_missing_columns_ddl,
    _open_ddl_connection,
    auto_ensure_schema,
    clear_schema_cache,
    _build_data_from_sql,
    SafeCursor,
    _schema_cache,
    _schema_lock,
)


# ======================== 纯函数 ========================

class TestInferSqlType:
    def test_int_sqlite(self):
        assert _infer_sql_type(42, True) == "INTEGER"

    def test_int_mysql(self):
        assert _infer_sql_type(42, False) == "INT"

    def test_float_sqlite(self):
        assert _infer_sql_type(3.14, True) == "REAL"

    def test_float_mysql(self):
        assert _infer_sql_type(3.14, False) == "DECIMAL(14,4)"

    def test_bool_sqlite(self):
        assert _infer_sql_type(True, True) == "INTEGER"

    def test_bool_mysql(self):
        assert _infer_sql_type(False, False) == "TINYINT(1)"

    def test_none_sqlite(self):
        assert _infer_sql_type(None, True) == "TEXT"

    def test_none_mysql(self):
        assert _infer_sql_type(None, False) == "TEXT"

    def test_dict(self):
        assert _infer_sql_type({"a": 1}, True) == "TEXT"

    def test_list(self):
        assert _infer_sql_type([1, 2], False) == "TEXT"

    def test_short_string_sqlite(self):
        assert _infer_sql_type("hello", True) == "TEXT"

    def test_short_string_mysql(self):
        assert _infer_sql_type("hello", False) == "VARCHAR(255)"

    def test_long_string_mysql(self):
        long_str = "x" * 300
        assert _infer_sql_type(long_str, False) == "TEXT"


class TestValidateName:
    @pytest.mark.parametrize("name,expected", [
        ("valid_name", True),
        ("table123", True),
        ("_private", True),
        ("123invalid", False),
        ("bad-name", False),
        ("has space", False),
        ("", False),
    ])
    def test_validate(self, name, expected):
        assert _validate_name(name) is expected


class TestGetDbIdentity:
    def test_mysql(self):
        conn = MagicMock()
        type(conn).__module__ = PropertyMock(return_value="pymysql.connections")
        conn.db = "test_db"
        ident = _get_db_identity(conn)
        assert ident == "mysql:test_db"

    def test_mysql_no_db_attr(self):
        conn = MagicMock(spec=[])
        type(conn).__module__ = PropertyMock(return_value="pymysql.connections")
        ident = _get_db_identity(conn)
        assert ident.startswith("mysql:")

    def test_sqlite(self):
        conn = MagicMock()
        type(conn).__module__ = PropertyMock(return_value="sqlite3.dbapi2")
        conn.database = "/tmp/test.db"
        ident = _get_db_identity(conn)
        assert ident == "sqlite:/tmp/test.db"

    def test_unknown(self):
        conn = MagicMock()
        type(conn).__module__ = PropertyMock(return_value="some.other.module")
        ident = _get_db_identity(conn)
        assert ident.startswith("unknown:")


class TestCheckTableExists:
    def test_sqlite_found(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = ("mytable",)
        assert _check_table_exists(cursor, "mytable", True) is True
        cursor.execute.assert_called_once_with(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", ("mytable",)
        )

    def test_mysql_not_found(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        assert _check_table_exists(cursor, "no_table", False) is False
        cursor.execute.assert_called_once_with("SHOW TABLES LIKE %s", ("no_table",))


class TestGetExistingColumns:
    def test_sqlite(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [(0, "id"), (1, "name")]
        cols = _get_existing_columns(cursor, "t", True)
        assert cols == {"id", "name"}

    def test_mysql(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [{"Field": "id"}, {"Field": "name"}]
        cols = _get_existing_columns(cursor, "t", False)
        assert cols == {"id", "name"}


class TestCreateTableDdl:
    def test_mysql(self):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        _create_table_ddl(conn, "test_tbl", {"id": "INT", "name": "VARCHAR(255)"}, False)
        sql = cursor.execute.call_args[0][0]
        assert "CREATE TABLE IF NOT EXISTS" in sql
        assert "ENGINE=InnoDB" in sql
        conn.commit.assert_called_once()

    def test_sqlite(self):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        _create_table_ddl(conn, "test_tbl", {"id": "INTEGER", "val": "TEXT"}, True)
        sql = cursor.execute.call_args[0][0]
        assert "CREATE TABLE IF NOT EXISTS" in sql
        assert "ENGINE" not in sql
        conn.commit.assert_called_once()

    def test_exception(self):
        conn = MagicMock()
        cursor = MagicMock()
        cursor.execute.side_effect = Exception("create failed")
        conn.cursor.return_value = cursor
        _create_table_ddl(conn, "bad", {"x": "TEXT"}, True)
        conn.rollback.assert_called_once()


class TestAddMissingColumnsDdl:
    def test_adds_columns(self):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        _add_missing_columns_ddl(conn, "tbl", {"col1": "TEXT", "col2": "INT"}, False)
        assert cursor.execute.call_count == 2
        conn.commit.assert_called_once()

    def test_partial_failure(self):
        conn = MagicMock()
        cursor = MagicMock()
        execute = MagicMock()
        execute.side_effect = [None, Exception("second failed")]
        conn.cursor.return_value.__enter__.return_value = MagicMock()
        conn.cursor.return_value = cursor
        # Use a real mock that can be called
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = [None, Exception("second failed")]
        conn.cursor.return_value = mock_cursor
        _add_missing_columns_ddl(conn, "tbl", {"a": "TEXT", "b": "INT"}, False)
        mock_cursor.execute.assert_any_call("ALTER TABLE `tbl` ADD COLUMN `a` TEXT")
        mock_cursor.execute.assert_any_call("ALTER TABLE `tbl` ADD COLUMN `b` INT")


class TestOpenDdlConnection:
    def test_mysql(self):
        conn = MagicMock()
        type(conn).__module__ = PropertyMock(return_value="pymysql.connections")
        conn.host = "localhost"
        conn.port = 3306
        conn.user = "root"
        conn.password = ""
        conn.db = "test"

        with patch("utils.auto_schema.pymysql") as mock_pymysql:
            result = _open_ddl_connection(conn)
            assert result is mock_pymysql.connect.return_value
            mock_pymysql.connect.assert_called_once_with(
                host="localhost", port=3306, user="root",
                password="", database="test", charset="utf8mb4",
            )

    def test_sqlite(self):
        conn = MagicMock()
        type(conn).__module__ = PropertyMock(return_value="sqlite3.dbapi2")
        conn.database = ":memory:"

        with patch("utils.auto_schema.sqlite3") as mock_sqlite3:
            result = _open_ddl_connection(conn)
            assert result is mock_sqlite3.connect.return_value
            mock_sqlite3.connect.assert_called_once_with(":memory:", timeout=10)

    def test_unknown(self):
        conn = MagicMock()
        type(conn).__module__ = PropertyMock(return_value="unknown.module")
        assert _open_ddl_connection(conn) is None


# ======================== auto_ensure_schema ========================

class TestAutoEnsureSchema:
    def _make_mysql_conn(self):
        conn = MagicMock()
        type(conn).__module__ = PropertyMock(return_value="pymysql.connections")
        conn.db = "test"
        return conn

    def _make_sqlite_conn(self):
        conn = MagicMock()
        type(conn).__module__ = PropertyMock(return_value="sqlite3.dbapi2")
        conn.database = ":memory:"
        return conn

    def setup_method(self):
        clear_schema_cache()

    def test_empty_data_returns(self):
        conn = self._make_mysql_conn()
        auto_ensure_schema(conn, "tbl", {})  # should not raise

    def test_empty_table_name_returns(self):
        conn = self._make_mysql_conn()
        auto_ensure_schema(conn, "", {"x": 1})

    def test_invalid_table_name_logs_warning(self, caplog):
        conn = self._make_mysql_conn()
        auto_ensure_schema(conn, "123bad", {"x": 1})
        assert "invalid table name" in caplog.text

    def test_cached_does_not_recheck(self):
        conn = self._make_mysql_conn()
        with patch("utils.auto_schema._check_table_exists") as mock_check:
            mock_check.return_value = True
            with patch("utils.auto_schema._get_existing_columns") as mock_cols:
                mock_cols.return_value = {"id", "x"}
                auto_ensure_schema(conn, "cached_tbl", {"x": 1})
                assert mock_check.call_count == 1
                assert mock_cols.call_count == 1

                # Second call with same key should hit cache
                auto_ensure_schema(conn, "cached_tbl", {"x": 1})
                assert mock_check.call_count == 1
                assert mock_cols.call_count == 1

    def test_table_not_exists_creates(self):
        conn = self._make_mysql_conn()
        cursor = MagicMock()
        cursor.fetchone.return_value = None  # table doesn't exist
        conn.cursor.return_value = cursor

        ddl_conn = MagicMock()
        ddl_cursor = MagicMock()
        ddl_conn.cursor.return_value = ddl_cursor

        with patch("utils.auto_schema._open_ddl_connection", return_value=ddl_conn):
            with patch("utils.auto_schema._create_table_ddl") as mock_create:
                auto_ensure_schema(conn, "new_tbl", {"name": "hello", "qty": 10})
                mock_create.assert_called_once()
                args = mock_create.call_args[0]
                assert args[1] == "new_tbl"
                assert "id" in args[2]
                assert "name" in args[2]
                assert "qty" in args[2]

    def test_existing_table_missing_columns(self):
        conn = self._make_mysql_conn()
        cursor = MagicMock()
        cursor.fetchone.return_value = ("new_tbl",)  # table exists
        conn.cursor.return_value = cursor

        # Mock existing columns to not have 'new_col'
        with patch("utils.auto_schema._get_existing_columns", return_value={"id", "name"}):
            with patch("utils.auto_schema._open_ddl_connection") as mock_ddl_open:
                ddl_conn = MagicMock()
                mock_ddl_open.return_value = ddl_conn
                with patch("utils.auto_schema._add_missing_columns_ddl") as mock_add:
                    auto_ensure_schema(conn, "new_tbl", {"name": "x", "new_col": 42})
                    mock_add.assert_called_once()
                    args = mock_add.call_args[0]
                    assert args[1] == "new_tbl"
                    assert "new_col" in args[2]

    def test_existing_table_no_missing_columns(self):
        conn = self._make_mysql_conn()
        cursor = MagicMock()
        cursor.fetchone.return_value = ("tbl",)
        conn.cursor.return_value = cursor

        with patch("utils.auto_schema._get_existing_columns", return_value={"id", "name", "qty"}):
            with patch("utils.auto_schema._open_ddl_connection") as mock_open:
                auto_ensure_schema(conn, "tbl", {"name": "x", "qty": 5})
                mock_open.assert_not_called()

    def test_ddl_conn_none_does_not_crash(self):
        conn = self._make_mysql_conn()
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        conn.cursor.return_value = cursor
        with patch("utils.auto_schema._open_ddl_connection", return_value=None):
            auto_ensure_schema(conn, "orphan", {"x": 1})  # should not raise


# ======================== _build_data_from_sql ========================

class TestBuildDataFromSql:
    def test_insert_basic(self):
        sql = "INSERT INTO `orders` (id, name) VALUES (%s, %s)"
        result = _build_data_from_sql(sql, (1, "test"))
        assert result is not None
        table, data = result
        assert table == "orders"
        assert data == {"id": 1, "name": "test"}

    def test_insert_or_ignore(self):
        sql = "INSERT OR IGNORE INTO logs (msg) VALUES (?)"
        result = _build_data_from_sql(sql, ("hello",))
        assert result is not None
        assert result[0] == "logs"

    def test_insert_on_duplicate(self):
        sql = "INSERT INTO t (a, b) VALUES (%s, %s) ON DUPLICATE KEY UPDATE b = VALUES(b)"
        result = _build_data_from_sql(sql, (1, 2))
        assert result is not None
        assert result[1] == {"a": 1, "b": 2}

    def test_update_basic(self):
        sql = "UPDATE users SET name = %s WHERE id = %s"
        result = _build_data_from_sql(sql, ("new", 42))
        assert result is not None
        assert result[0] == "users"
        assert result[1] == {"name": "new"}

    def test_update_multiple_cols(self):
        sql = "UPDATE items SET qty = %s, price = %s WHERE id = %s"
        result = _build_data_from_sql(sql, (10, 99.5, 1))
        assert result is not None
        assert result[1] == {"qty": 10, "price": 99.5}

    def test_select_returns_none(self):
        sql = "SELECT * FROM users WHERE id = %s"
        result = _build_data_from_sql(sql, (1,))
        assert result is None

    def test_params_none_returns_none(self):
        sql = "INSERT INTO t (a) VALUES (%s)"
        result = _build_data_from_sql(sql, None)
        assert result is None

    def test_empty_cols_returns_none(self):
        sql = "INSERT INTO t () VALUES ()"
        result = _build_data_from_sql(sql, ())
        assert result is None


# ======================== SafeCursor ========================

class TestSafeCursor:
    def test_execute_calls_auto_ensure(self):
        cursor = MagicMock()
        conn = MagicMock()
        type(conn).__module__ = PropertyMock(return_value="pymysql.connections")
        conn.db = "test"

        safe = SafeCursor(cursor, conn)
        with patch("utils.auto_schema.auto_ensure_schema") as mock_ensure:
            safe.execute("INSERT INTO t (x) VALUES (%s)", (42,))
            mock_ensure.assert_called_once()

    def test_execute_non_insert_skips_ensure(self):
        cursor = MagicMock()
        conn = MagicMock()

        safe = SafeCursor(cursor, conn)
        with patch("utils.auto_schema.auto_ensure_schema") as mock_ensure:
            safe.execute("SELECT 1")
            mock_ensure.assert_not_called()

    def test_execute_replaces_qmark_for_mysql(self):
        cursor = MagicMock()
        conn = MagicMock()
        type(conn).__module__ = PropertyMock(return_value="pymysql.connections")
        conn.db = "test"

        safe = SafeCursor(cursor, conn)
        safe.execute("INSERT INTO t (x) VALUES (?)", (1,))
        call_query = cursor.execute.call_args[0][0]
        assert "%s" in call_query
        assert "?" not in call_query

    def test_executemany_calls_auto_ensure(self):
        cursor = MagicMock()
        conn = MagicMock()
        type(conn).__module__ = PropertyMock(return_value="pymysql.connections")
        conn.db = "test"

        safe = SafeCursor(cursor, conn)
        with patch("utils.auto_schema.auto_ensure_schema") as mock_ensure:
            safe.executemany("INSERT INTO t (x) VALUES (%s)", [(1,), (2,)])
            mock_ensure.assert_called_once()

    def test_iter_delegates(self):
        cursor = MagicMock()
        cursor.__iter__.return_value = iter([1, 2, 3])
        safe = SafeCursor(cursor, MagicMock())
        assert list(safe) == [1, 2, 3]

    def test_context_manager(self):
        cursor = MagicMock()
        conn = MagicMock()
        with SafeCursor(cursor, conn) as safe:
            assert safe is not None

    def test_getattr_delegates(self):
        cursor = MagicMock()
        cursor.rowcount = 5
        safe = SafeCursor(cursor, MagicMock())
        assert safe.rowcount == 5
