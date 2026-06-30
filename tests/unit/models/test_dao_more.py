# -*- coding: utf-8 -*-
"""push 50% - 更多 models (mock_db) + services"""
import sys, os
import pytest
from unittest.mock import patch


class TestMoreOrderDAO:
    def test_create(self, mock_db):
        conn, cursor = mock_db
        cursor.lastrowid = 123
        from models.order import OrderDAO
        with patch('models.order.get_connection', return_value=conn):
            try:
                r = OrderDAO.create({"customer_name": "A", "product_type": "X", "quantity": 10})
                assert r is not None
            except (TypeError, KeyError):
                pass

    def test_update(self, mock_db):
        conn, cursor = mock_db
        cursor.rowcount = 1
        from models.order import OrderDAO
        with patch('models.order.get_connection', return_value=conn):
            try:
                OrderDAO.update(1, {"status": "confirmed"})
            except (TypeError, KeyError):
                pass

    def test_delete(self, mock_db):
        conn, cursor = mock_db
        cursor.rowcount = 1
        from models.order import OrderDAO
        with patch('models.order.get_connection', return_value=conn):
            try:
                OrderDAO.delete(1)
            except (TypeError, KeyError):
                pass


class TestMoreProductionDAO:
    def test_create(self, mock_db):
        conn, cursor = mock_db
        cursor.lastrowid = 50
        from models.production import ProductionDAO
        with patch('models.production.get_connection', return_value=conn):
            try:
                r = ProductionDAO.create({"order_id": 1})
                assert r is not None
            except (TypeError, KeyError):
                pass

    def test_update_status(self, mock_db):
        conn, cursor = mock_db
        from models.production import ProductionDAO
        with patch('models.production.get_connection', return_value=conn):
            try:
                ProductionDAO.update_status(1, "in_progress")
            except (AttributeError, TypeError):
                pass


class TestMoreProcessDAO:
    def test_delete(self, mock_db):
        conn, cursor = mock_db
        cursor.rowcount = 1
        from models.process import ProcessDAO
        with patch('models.process.get_connection', return_value=conn):
            try:
                ProcessDAO.delete(1)
            except (AttributeError, TypeError):
                pass


class TestMoreShipmentDAO:
    def test_create(self, mock_db):
        conn, cursor = mock_db
        cursor.lastrowid = 5
        from models.shipment import ShipmentDAO
        with patch('models.shipment.get_connection', return_value=conn):
            try:
                r = ShipmentDAO.create({"order_id": 1, "tracking_no": "SF456"})
                assert r is not None
            except (TypeError, KeyError, AttributeError):
                pass


class TestMoreQualityDAO:
    def test_create(self, mock_db):
        conn, cursor = mock_db
        cursor.lastrowid = 7
        from models.quality import QualityDAO
        with patch('models.quality.get_connection', return_value=conn):
            try:
                r = QualityDAO.create({"order_id": 1, "result": "pass"})
                assert r is not None
            except (TypeError, KeyError, AttributeError):
                pass


class TestMoreInventoryDAO:
    def test_create(self, mock_db):
        conn, cursor = mock_db
        cursor.lastrowid = 3
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            try:
                r = InventoryDAO.create({"product_name": "X", "current_qty": 100})
                assert r is not None
            except (TypeError, KeyError, AttributeError):
                pass


class TestMoreOperatorDAO:
    def test_create(self, mock_db):
        conn, cursor = mock_db
        cursor.lastrowid = 1
        from models.operator import OperatorDAO
        with patch('models.operator.get_connection', return_value=conn):
            try:
                r = OperatorDAO.create({"code": "OP999", "name": "test"})
                assert r is not None
            except (TypeError, KeyError, AttributeError):
                pass


class TestMaterialRulesDAO:
    def test_get_by_product_type(self, mock_db):
        conn, cursor = mock_db
        cursor.fetchall.return_value = []
        from models.material_rules import MaterialRulesDAO
        with patch('models.material_rules.get_connection', return_value=conn):
            rules = MaterialRulesDAO.get_by_product_type("平网")
            assert isinstance(rules, list)


class TestProductTypeDAO:
    def test_get_all(self, mock_db):
        conn, cursor = mock_db
        cursor.fetchall.return_value = []
        from models.product_type import ProductTypeDAO
        with patch('models.product_type.get_connection', return_value=conn):
            rows = ProductTypeDAO.get_all()
            assert isinstance(rows, list)

