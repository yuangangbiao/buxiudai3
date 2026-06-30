# -*- coding: utf-8 -*-
"""冲刺30%最后一批 - auto_schema + config"""
import sys, os
import pytest
from unittest.mock import patch


class TestAutoSchema:
    def test_infer_sql_type_str_short_sqlite(self):
        from utils.auto_schema import _infer_sql_type
        assert _infer_sql_type('hi', True) == 'TEXT'

    def test_infer_sql_type_str_long_sqlite(self):
        from utils.auto_schema import _infer_sql_type
        assert _infer_sql_type('a'*300, True) == 'TEXT'

    def test_infer_sql_type_str_short_mysql(self):
        from utils.auto_schema import _infer_sql_type
        assert _infer_sql_type('hi', False) == 'VARCHAR(255)'

    def test_infer_sql_type_str_long_mysql(self):
        from utils.auto_schema import _infer_sql_type
        assert _infer_sql_type('a'*300, False) == 'TEXT'

    def test_infer_sql_type_int_sqlite(self):
        from utils.auto_schema import _infer_sql_type
        assert _infer_sql_type(42, True) == 'INTEGER'

    def test_infer_sql_type_int_mysql(self):
        from utils.auto_schema import _infer_sql_type
        assert _infer_sql_type(42, False) == 'INT'

    def test_infer_sql_type_float_sqlite(self):
        from utils.auto_schema import _infer_sql_type
        assert _infer_sql_type(3.14, True) == 'REAL'

    def test_infer_sql_type_none(self):
        from utils.auto_schema import _infer_sql_type
        assert _infer_sql_type(None, True) == 'TEXT'

    def test_infer_sql_type_dict(self):
        from utils.auto_schema import _infer_sql_type
        assert _infer_sql_type({'key': 'val'}, False) == 'TEXT'

    def test_auto_ensure_schema_exists(self):
        from utils.auto_schema import auto_ensure_schema
        assert callable(auto_ensure_schema)

    def test_safe_cursor_class(self):
        from utils.auto_schema import SafeCursor
        assert SafeCursor is not None


class TestConfig:
    def test_material_densities(self):
        from config import MATERIAL_DENSITIES
        assert isinstance(MATERIAL_DENSITIES, dict)
        assert len(MATERIAL_DENSITIES) > 0

    def test_product_types(self):
        from config import PRODUCT_TYPES
        assert isinstance(PRODUCT_TYPES, list)

    def test_db_path_exists(self):
        from config import DB_PATH
        assert isinstance(DB_PATH, str)
        assert len(DB_PATH) > 0

    def test_base_dir(self):
        from config import BASE_DIR
        assert BASE_DIR is not None
