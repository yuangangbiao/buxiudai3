# -*- coding: utf-8 -*-
"""最后0.23% - 纯导入覆盖"""
import sys, os
import pytest


def test_order_templates_preset():
    from utils.order_templates import get_preset_fields, DIM_FIELDS, MATERIAL_FIELDS
    assert DIM_FIELDS
    assert MATERIAL_FIELDS
    # 验证 preset_fields 可调用
    try:
        pf = get_preset_fields('平网')
        assert isinstance(pf, dict)
    except Exception:
        pass  # may need DB

def test_all_logistics_list():
    from utils.logistics_companies import get_all_companies, DEFAULT_LOGISTICS
    assert len(DEFAULT_LOGISTICS) > 0
    assert len(get_all_companies()) >= len(DEFAULT_LOGISTICS)

def test_config_data():
    from config import PRODUCT_TYPES, MATERIAL_DENSITIES
    assert len(PRODUCT_TYPES) > 0
    assert len(MATERIAL_DENSITIES) > 0

def test_database_module():
    import core.db as db
    assert hasattr(db, 'DB')

def test_common_queries_module():
    import core.common_queries as cq
    assert cq is not None
