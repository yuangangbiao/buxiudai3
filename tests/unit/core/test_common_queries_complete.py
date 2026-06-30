# -*- coding: utf-8 -*-
"""
core/common_queries.py 测试 - SQL构建函数
"""
import pytest


class TestCommonQueriesFindById:
    """find_by_id 测试"""

    def test_find_by_id_default(self):
        from core.common_queries import find_by_id
        sql, params = find_by_id("orders", 1)
        assert "SELECT * FROM orders WHERE id = %s" in sql
        assert params == (1,)

    def test_find_by_id_custom_column(self):
        from core.common_queries import find_by_id
        sql, params = find_by_id("orders", "ORD-001", id_column="order_no")
        assert "WHERE order_no = %s" in sql
        assert params == ("ORD-001",)

    def test_find_by_id_custom_columns(self):
        from core.common_queries import find_by_id
        sql, params = find_by_id("orders", 1, columns="id, order_no, status")
        assert sql == "SELECT id, order_no, status FROM orders WHERE id = %s"


class TestCommonQueriesFindByColumn:
    """find_by_column 测试"""

    def test_find_by_column(self):
        from core.common_queries import find_by_column
        sql, params = find_by_column("orders", "status", "生产中")
        assert "WHERE status = %s" in sql
        assert params == ("生产中",)

    def test_find_by_column_custom_columns(self):
        from core.common_queries import find_by_column
        sql, params = find_by_column("orders", "status", "生产中", columns="id, order_no")
        assert "SELECT id, order_no FROM orders" in sql


class TestCommonQueriesFindAllByColumn:
    """find_all_by_column 测试"""

    def test_find_all_by_column(self):
        from core.common_queries import find_all_by_column
        sql, params = find_all_by_column("orders", "status", "生产中")
        assert "WHERE status = %s" in sql
        assert params == ("生产中",)

    def test_find_all_with_order_by(self):
        from core.common_queries import find_all_by_column
        sql, params = find_all_by_column("orders", "status", "生产中", order_by="created_at DESC")
        assert "ORDER BY created_at DESC" in sql

    def test_find_all_with_extra_conditions(self):
        from core.common_queries import find_all_by_column
        sql, params = find_all_by_column("orders", "status", "生产中", extra_conditions="is_deleted=0")
        assert "AND is_deleted=0" in sql


class TestCommonQueriesAggregate:
    """aggregate 测试"""

    def test_aggregate_basic(self):
        from core.common_queries import aggregate
        sql, params = aggregate("orders", "COUNT(*)")
        assert "SELECT COUNT(*) FROM orders" in sql
        assert params == ()

    def test_aggregate_with_where(self):
        from core.common_queries import aggregate
        sql, params = aggregate("orders", "SUM(amount)", where_column="status", where_value="已完成")
        assert "WHERE status = %s" in sql
        assert params == ("已完成",)

    def test_aggregate_with_extra_conditions(self):
        from core.common_queries import aggregate
        sql, params = aggregate("orders", "COUNT(*)", extra_conditions="created_at >= NOW()")
        assert "WHERE created_at >= NOW()" in sql
        assert params == ()

    def test_aggregate_with_where_and_extra(self):
        from core.common_queries import aggregate
        sql, params = aggregate("orders", "COUNT(*)", where_column="status", where_value="生产中", extra_conditions="is_deleted=0")
        assert "WHERE status = %s AND is_deleted=0" in sql
        assert params == ("生产中",)


class TestCommonQueriesUpsertSelect:
    """upsert_select 测试"""

    def test_upsert_select_default(self):
        from core.common_queries import upsert_select
        sql, params = upsert_select("orders", "order_no", "ORD-001")
        assert "WHERE order_no = %s" in sql
        assert params == ("ORD-001",)

    def test_upsert_select_custom_columns(self):
        from core.common_queries import upsert_select
        sql, params = upsert_select("orders", "order_no", "ORD-001", columns="id, status")
        assert "SELECT id, status FROM orders" in sql
