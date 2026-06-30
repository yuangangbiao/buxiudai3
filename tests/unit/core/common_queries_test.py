# -*- coding: utf-8 -*-
"""Tests for core.common_queries — pure SQL builder functions."""

import pytest
from core.common_queries import (
    find_by_id,
    find_by_column,
    find_all_by_column,
    aggregate,
    upsert_select,
)


class TestFindById:
    def test_basic(self):
        sql, params = find_by_id("orders", 42)
        assert sql == "SELECT * FROM orders WHERE id = %s"
        assert params == (42,)

    def test_custom_column(self):
        sql, params = find_by_id("users", "abc-123", id_column="uuid", columns="id, name")
        assert "SELECT id, name" in sql
        assert "uuid = %s" in sql
        assert params == ("abc-123",)


class TestFindByColumn:
    def test_basic(self):
        sql, params = find_by_column("products", "sku", "SKU-001")
        assert sql == "SELECT * FROM products WHERE sku = %s"
        assert params == ("SKU-001",)

    def test_custom_columns(self):
        sql, params = find_by_column("items", "status", "active", columns="id")
        assert sql == "SELECT id FROM items WHERE status = %s"
        assert params == ("active",)


class TestFindAllByColumn:
    def test_basic(self):
        sql, params = find_all_by_column("orders", "customer_id", 5)
        assert sql == "SELECT * FROM orders WHERE customer_id = %s"
        assert params == (5,)

    def test_with_order_by(self):
        sql, _ = find_all_by_column("orders", "status", "new", order_by="created_at DESC")
        assert "ORDER BY created_at DESC" in sql

    def test_with_extra_conditions(self):
        sql, _ = find_all_by_column("tasks", "assignee", "alice", extra_conditions="status != 'done'")
        assert "AND status != 'done'" in sql

    def test_with_order_and_extra(self):
        sql, _ = find_all_by_column(
            "logs", "level", "ERROR",
            columns="id, message",
            order_by="timestamp DESC",
            extra_conditions="created_at > '2024-01-01'",
        )
        assert "ORDER BY timestamp DESC" in sql
        assert "AND created_at > '2024-01-01'" in sql
        assert "SELECT id, message" in sql


class TestAggregate:
    def test_no_where(self):
        sql, params = aggregate("orders", "COUNT(*)")
        assert sql == "SELECT COUNT(*) FROM orders"
        assert params == ()

    def test_with_where(self):
        sql, params = aggregate("orders", "SUM(total)", where_column="status", where_value="completed")
        assert sql == "SELECT SUM(total) FROM orders WHERE status = %s"
        assert params == ("completed",)

    def test_with_extra_conditions(self):
        sql, params = aggregate(
            "inventory", "COUNT(*)",
            where_column="warehouse",
            where_value="A",
            extra_conditions="quantity > 0",
        )
        assert "quantity > 0" in sql
        assert "warehouse = %s" in sql
        assert params == ("A",)

    def test_extra_only_no_where(self):
        sql, params = aggregate("items", "AVG(price)", extra_conditions="deleted = 0")
        assert "WHERE deleted = 0" in sql
        assert sql.startswith("SELECT AVG(price)")
        assert params == ()


class TestUpsertSelect:
    def test_basic(self):
        sql, params = upsert_select("products", "product_code", "P001")
        assert sql == "SELECT id FROM products WHERE product_code = %s"
        assert params == ("P001",)

    def test_custom_columns(self):
        sql, params = upsert_select("users", "email", "a@b.com", columns="id, name")
        assert sql == "SELECT id, name FROM users WHERE email = %s"
        assert params == ("a@b.com",)
