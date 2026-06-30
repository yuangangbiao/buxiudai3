# -*- coding: utf-8 -*-
r"""core/common_queries.py 的集成测试。

真源码行为(已读 d:\yuan\不锈钢网带跟单3.0\core\common_queries.py 验证):
- 5 个纯函数,不调 DB,只生成 (sql, params) tuple
- find_by_id(table, id_value, id_column='id', columns='*') → SELECT
- find_by_column(table, column, value, columns='*') → SELECT WHERE column = %s
- find_all_by_column(table, column, value, columns='*', order_by=None, extra_conditions='') → SELECT WHERE column = %s + 可选 AND + 可选 ORDER BY
- aggregate(table, expressions, where_column=None, where_value=None, extra_conditions='') → SELECT expressions + 可选 WHERE
- upsert_select(table, key_column, key_value, columns='id') → SELECT

按 F16 §1:不 mock 业务路径(纯函数,直接调验证 SQL 字符串和 params)。
"""
import pytest

from core.common_queries import (
    find_by_id, find_by_column, find_all_by_column,
    aggregate, upsert_select,
)


def test_find_by_id_returns_select_with_default_id():
    r"""find_by_id 默认 id_column='id',生成 SELECT * FROM table WHERE id = %s。"""
    sql, params = find_by_id("orders", 123)
    assert sql == "SELECT * FROM orders WHERE id = %s"
    assert params == (123,)


def test_find_by_id_custom_id_column():
    r"""find_by_id 传 id_column='order_no' 时,WHERE 用 order_no。"""
    sql, params = find_by_id("orders", "GO-001", id_column="order_no")
    assert sql == "SELECT * FROM orders WHERE order_no = %s"
    assert params == ("GO-001",)


def test_find_by_id_custom_columns():
    r"""find_by_id columns='id, name' 时,SELECT 含指定列。"""
    sql, params = find_by_id("users", 5, columns="id, name")
    assert sql == "SELECT id, name FROM users WHERE id = %s"
    assert params == (5,)


def test_find_by_column_returns_select():
    r"""find_by_column 生成 SELECT WHERE column = %s。"""
    sql, params = find_by_column("orders", "status", "生产中")
    assert sql == "SELECT * FROM orders WHERE status = %s"
    assert params == ("生产中",)


def test_find_by_column_custom_columns():
    r"""find_by_column columns='id, name' 时,SELECT 含指定列。"""
    sql, params = find_by_column("users", "email", "test@example.com", columns="id, name")
    assert sql == "SELECT id, name FROM users WHERE email = %s"
    assert params == ("test@example.com",)


def test_find_all_by_column_basic():
    r"""find_all_by_column 无 order_by/extra 时,WHERE column = %s。"""
    sql, params = find_all_by_column("orders", "customer_id", 100)
    assert sql == "SELECT * FROM orders WHERE customer_id = %s"
    assert params == (100,)


def test_find_all_by_column_with_order_by():
    r"""find_all_by_column order_by='created_at DESC' 时,SQL 含 ORDER BY。"""
    sql, params = find_all_by_column("orders", "status", "已完成", order_by="created_at DESC")
    assert sql == "SELECT * FROM orders WHERE status = %s ORDER BY created_at DESC"
    assert params == ("已完成",)


def test_find_all_by_column_with_extra_conditions():
    r"""find_all_by_column extra_conditions='is_active=1' 时,SQL 含 AND。"""
    sql, params = find_all_by_column("users", "role", "admin", extra_conditions="is_active=1")
    assert sql == "SELECT * FROM users WHERE role = %s AND is_active=1"
    assert params == ("admin",)


def test_find_all_by_column_with_order_and_extra():
    r"""find_all_by_column 同时有 order_by 和 extra_conditions。"""
    sql, params = find_all_by_column(
        "orders", "status", "生产中",
        order_by="created_at ASC",
        extra_conditions="priority>0",
    )
    assert sql == "SELECT * FROM orders WHERE status = %s AND priority>0 ORDER BY created_at ASC"
    assert params == ("生产中",)


def test_aggregate_no_where():
    r"""aggregate 不传 where 时,只有 SELECT expressions。"""
    sql, params = aggregate("orders", "COUNT(*)")
    assert sql == "SELECT COUNT(*) FROM orders"
    assert params == ()


def test_aggregate_with_where():
    r"""aggregate where_column+where_value 时,WHERE column = %s。"""
    sql, params = aggregate("orders", "SUM(weight)", where_column="status", where_value="已完成")
    assert sql == "SELECT SUM(weight) FROM orders WHERE status = %s"
    assert params == ("已完成",)


def test_aggregate_with_extra_conditions():
    r"""aggregate extra_conditions 时,WHERE 用 AND 连接(源码第 56-59 行)。"""
    sql, params = aggregate(
        "orders", "AVG(price)",
        where_column="status", where_value="已完成",
        extra_conditions="created_at > '2026-01-01'",
    )
    assert sql == "SELECT AVG(price) FROM orders WHERE status = %s AND created_at > '2026-01-01'"
    assert params == ("已完成",)


def test_aggregate_with_only_extra_conditions():
    r"""aggregate 只传 extra_conditions 不传 where 时,WHERE 只含 extra。"""
    sql, params = aggregate("orders", "COUNT(*)", extra_conditions="status='已完成'")
    assert sql == "SELECT COUNT(*) FROM orders WHERE status='已完成'"
    assert params == ()


def test_upsert_select_returns_select():
    r"""upsert_select 生成 SELECT WHERE key_column = %s。"""
    sql, params = upsert_select("orders", "order_no", "GO-001")
    assert sql == "SELECT id FROM orders WHERE order_no = %s"
    assert params == ("GO-001",)


def test_upsert_select_custom_columns():
    r"""upsert_select columns='id, status' 时,SELECT 含指定列。"""
    sql, params = upsert_select("orders", "order_no", "GO-001", columns="id, status")
    assert sql == "SELECT id, status FROM orders WHERE order_no = %s"
    assert params == ("GO-001",)
