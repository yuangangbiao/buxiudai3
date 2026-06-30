# -*- coding: utf-8 -*-
"""excel_utils.py 全覆盖测试"""
import sys, os
import pytest, openpyxl
from unittest.mock import patch, MagicMock


class TestExcelStyles:
    def test_header_fill(self):
        from utils.excel_utils import ExcelExporter
        assert ExcelExporter.HEADER_FILL is not None

    def test_header_font(self):
        from utils.excel_utils import ExcelExporter
        assert ExcelExporter.HEADER_FONT.bold is True


class TestRender:
    def test_set_header(self):
        from utils.excel_utils import ExcelExporter
        wb = openpyxl.Workbook(); ws = wb.active
        ExcelExporter._set_header(ws, ["A", "B"])

    def test_set_data_row(self):
        from utils.excel_utils import ExcelExporter
        wb = openpyxl.Workbook(); ws = wb.active
        ExcelExporter._set_data_row(ws, 3, ["x", 42])

    def test_auto_width(self):
        from utils.excel_utils import ExcelExporter
        wb = openpyxl.Workbook(); ws = wb.active
        ws.cell(1, 1, "short"); ws.cell(1, 2, "long_value_here")
        ExcelExporter._auto_width(ws)


class TestExportOrders:
    def test_export(self, tmp_path):
        from utils.excel_utils import ExcelExporter
        fp = os.path.join(str(tmp_path), 'orders.xlsx')
        row = {"order_no": "ORD-001", "customer_name": "A", "customer_phone": "",
               "customer_address": "", "product_type": "X", "material": "304",
               "mesh_size": 12, "wire_diameter": 2.0, "width": 100, "length": 50,
               "quantity": 100, "unit": "米", "unit_price": 15.0, "total_amount": 1500.0,
               "surface_treatment": "", "special_requirements": "",
               "delivery_date": "", "status": "pending", "remark": "",
               "extra_params": "", "created_at": "", "updated_at": ""}
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.fetchall.return_value = [row]
        with patch('models.database.get_connection', return_value=mock_conn):
            assert ExcelExporter.export_orders(fp) is True

    def test_export_empty(self, tmp_path):
        from utils.excel_utils import ExcelExporter
        fp = os.path.join(str(tmp_path), 'empty.xlsx')
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.fetchall.return_value = []
        with patch('models.database.get_connection', return_value=mock_conn):
            assert ExcelExporter.export_orders(fp) is True


class TestExportInventory:
    def test_export(self, tmp_path):
        from utils.excel_utils import ExcelExporter
        fp = os.path.join(str(tmp_path), 'inv.xlsx')
        row = {"material_name": "304", "material_type": "不锈钢", "specification": "2mm",
               "quantity": 500, "unit": "kg", "unit_price": 25.0,
               "warehouse": "A", "warning_qty": 50, "remark": "", "updated_at": ""}
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.fetchall.return_value = [row]
        with patch('models.database.get_connection', return_value=mock_conn):
            assert ExcelExporter.export_inventory(fp) is True


class TestExportBom:
    def test_export(self, tmp_path):
        from utils.excel_utils import ExcelExporter
        fp = os.path.join(str(tmp_path), 'bom.xlsx')
        row = {"product_type": "平网", "material": "304", "steel_weight": 5.0,
               "steel_unit": "kg/m", "waste_rate": 5, "packaging_materials": "",
               "surface_treatment": "", "production_process": "", "unit": "kg",
               "remark": "", "created_at": ""}
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.fetchall.return_value = [row]
        with patch('models.database.get_connection', return_value=mock_conn):
            assert ExcelExporter.export_bom(fp) is True


class TestExportMaterial:
    def test_export(self, tmp_path):
        from utils.excel_utils import ExcelExporter
        fp = os.path.join(str(tmp_path), 'mat.xlsx')
        row = {"order_no": "ORD-1", "customer_name": "A", "material_name": "304",
               "material_type": "不锈钢", "required_qty": 100, "prepared_qty": 50,
               "unit": "kg", "prep_status": "进行中", "warehouse": "A", "remark": ""}
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.fetchall.return_value = [row]
        with patch('models.database.get_connection', return_value=mock_conn):
            assert ExcelExporter.export_material_prep(fp) is True
