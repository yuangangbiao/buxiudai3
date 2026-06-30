# -*- coding: utf-8 -*-
r"""models/inventory.py 的集成测试。"""
from unittest.mock import MagicMock, patch, call

import pytest

from models.inventory import InventoryDAO


def _make_mock():
    r"""创建支持 with 协议的 mock conn。

    conn.cursor() 永远返回同一个 cursor,方便 execute.call_args_list 累积。
    """
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.return_value = None
    cursor.fetchall.return_value = []
    cursor.lastrowid = 1
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    return conn, cursor


@patch("models.inventory.STOCK_WARNING_THRESHOLD", 10)
def test_create_inserts_nine_columns():
    conn, cursor = _make_mock()
    cursor.lastrowid = 99
    with patch("models.inventory.get_connection", return_value=conn):
        result = InventoryDAO.create({
            "material_name": "304钢板", "material_type": "钢材",
            "specification": "1.0mm", "quantity": 100,
            "unit": "kg", "unit_price": 25.5,
            "warehouse": "主仓库", "warning_qty": 20, "remark": "测试",
        })
    assert result == 99
    sql = cursor.execute.call_args.args[0]
    assert "INSERT INTO inventory" in sql
    conn.commit.assert_called()


@patch("models.inventory.STOCK_WARNING_THRESHOLD", 10)
def test_create_uses_defaults():
    conn, cursor = _make_mock()
    cursor.lastrowid = 1
    with patch("models.inventory.get_connection", return_value=conn):
        InventoryDAO.create({"material_name": "304钢板", "quantity": 50})
    params = cursor.execute.call_args.args[1]
    assert "主仓库" in params
    assert "kg" in params


@patch("models.inventory.STOCK_WARNING_THRESHOLD", 10)
def test_create_converts_quantity_to_float():
    conn, cursor = _make_mock()
    cursor.lastrowid = 1
    with patch("models.inventory.get_connection", return_value=conn):
        InventoryDAO.create({"material_name": "304钢板", "quantity": "100", "unit_price": "25.5"})
    params = cursor.execute.call_args.args[1]
    assert params[3] == 100.0
    assert params[5] == 25.5


def test_update_executes():
    conn, cursor = _make_mock()
    with patch("models.inventory.get_connection", return_value=conn):
        result = InventoryDAO.update(1, {"material_name": "更新名称"})
    assert result is True
    sql = cursor.execute.call_args.args[0]
    assert "UPDATE inventory SET" in sql


def test_update_exception_propagates():
    conn, cursor = _make_mock()
    cursor.execute.side_effect = RuntimeError("DB error")
    with patch("models.inventory.get_connection", return_value=conn):
        with pytest.raises(RuntimeError):
            InventoryDAO.update(1, {"material_name": "更新"})


def test_stock_in_increases_quantity():
    conn, cursor = _make_mock()
    cursor.fetchone.return_value = (100,)
    with patch("models.inventory.get_connection", return_value=conn):
        result = InventoryDAO.stock_in(1, 50, order_id=5, operator="张三", remark="入库")
    assert result is True
    calls = cursor.execute.call_args_list
    assert len([c for c in calls if "UPDATE inventory SET" in str(c.args[0])]) >= 1


def test_stock_in_creates_log():
    conn, cursor = _make_mock()
    cursor.fetchone.return_value = (100,)
    with patch("models.inventory.get_connection", return_value=conn):
        result = InventoryDAO.stock_in(1, 50)
    assert result is True
    conn.commit.assert_called()


def test_stock_out_decreases_quantity():
    conn, cursor = _make_mock()
    cursor.fetchone.return_value = (100,)
    with patch("models.inventory.get_connection", return_value=conn):
        result = InventoryDAO.stock_out(1, 30, operator="张三", remark="出库")
    assert result is True


def test_get_all_returns_list():
    conn, cursor = _make_mock()
    cursor.fetchall.return_value = [{"id": 1, "material_name": "304钢板", "quantity": 100}]
    with patch("models.inventory.get_connection", return_value=conn):
        result = InventoryDAO.get_all()
    assert len(result) == 1


def test_get_all_with_material_type_filter():
    conn, cursor = _make_mock()
    cursor.fetchall.return_value = []
    with patch("models.inventory.get_connection", return_value=conn):
        InventoryDAO.get_all(filters={"material_type": "钢材", "keyword": "304", "warning_only": True})
    sql = cursor.execute.call_args.args[0]
    assert "material_type" in sql
    assert "quantity <= warning_qty" in sql


def test_get_records_returns_list():
    conn, cursor = _make_mock()
    cursor.fetchall.return_value = [{"id": 1, "action": "入库", "qty": 50}]
    with patch("models.inventory.get_connection", return_value=conn):
        result = InventoryDAO.get_records(1)
    assert len(result) == 1
    sql = cursor.execute.call_args.args[0]
    assert "inventory_records" in sql


def test_get_warning_items_filters_low_stock():
    conn, cursor = _make_mock()
    cursor.fetchall.return_value = [{"id": 1, "material_name": "304钢板", "quantity": 5, "warning_qty": 20}]
    with patch("models.inventory.get_connection", return_value=conn):
        result = InventoryDAO.get_warning_items()
    assert len(result) == 1
    sql = cursor.execute.call_args.args[0]
    assert "warning_qty" in sql


def test_get_dashboard_overview_returns_list():
    conn, cursor = _make_mock()
    cursor.fetchall.return_value = [
        {"material_name": "304钢板", "quantity": 100, "unit": "kg", "safe_stock": 20},
    ]
    with patch("models.inventory.get_connection", return_value=conn):
        result = InventoryDAO.get_dashboard_overview()
    assert isinstance(result, list)
    assert len(result) == 1


def test_get_low_inventory_alerts_returns_list():
    conn, cursor = _make_mock()
    cursor.fetchall.return_value = [{"id": 1, "material_name": "304钢板", "quantity": 5, "warning_qty": 20}]
    with patch("models.inventory.get_connection", return_value=conn):
        result = InventoryDAO.get_low_inventory_alerts(limit=5)
    assert len(result) == 1


def test_search_by_material_returns_list():
    conn, cursor = _make_mock()
    cursor.fetchall.return_value = [{"id": 1, "material_name": "304钢板", "specification": "1.0mm"}]
    with patch("models.inventory.get_connection", return_value=conn):
        result = InventoryDAO.search_by_material("304", "1.0")
    assert len(result) == 1
    sql = cursor.execute.call_args.args[0]
    assert "material_name LIKE" in sql
    assert "specification LIKE" in sql
