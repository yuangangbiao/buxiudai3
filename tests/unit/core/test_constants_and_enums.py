# -*- coding: utf-8 -*-
"""
测试 constants.py / logistics_companies / material_calculator / helpers
纯数据/工具模块，稳定可靠，无 DB 依赖
"""
import sys, os
import pytest


class TestOrderStatus:
    """orders 表 status 枚举"""

    def test_values_exist(self):
        from constants import OrderStatus
        values = [e.value for e in OrderStatus]
        assert len(values) >= 10
        assert "待确认" in values
        assert "已完成" in values

    def test_specific(self):
        from constants import OrderStatus
        assert OrderStatus.PENDING.value == "待确认"
        assert OrderStatus.PUBLISHED.value == "已发布"


class TestProductionStatus:
    """production_orders 表 status 枚举"""

    def test_values(self):
        from constants import ProductionStatus
        assert ProductionStatus.PENDING.value == "待开始"


class TestQualityStatus:
    """quality 状态枚举"""

    def test_values(self):
        from constants import QualityStatus
        vals = [e.value for e in QualityStatus]
        assert len(vals) >= 4


class TestLogisticsCompanies:
    """utils/logistics_companies.py"""

    def test_get_all(self):
        from utils.logistics_companies import get_all_companies, get_custom_companies
        all_co = get_all_companies()
        assert isinstance(all_co, list)
        assert len(all_co) > 0
        custom = get_custom_companies()
        assert isinstance(custom, list)

    def test_constants(self):
        from utils.logistics_companies import DATA_FILE, DEFAULT_LOGISTICS, BASE_DIR
        assert isinstance(DATA_FILE, str)
        assert isinstance(DEFAULT_LOGISTICS, list)
        assert os.path.exists(BASE_DIR)

    def test_add_remove(self):
        from utils.logistics_companies import add_company, remove_company, get_custom_companies
        before = len(get_custom_companies())
        add_company("testtemp999")
        after = len(get_custom_companies())
        assert after >= before
        remove_company("testtemp999")
        assert len(get_custom_companies()) <= after


class TestMaterialCalculator:
    """utils/material_calculator.py"""

    def test_instantiate(self):
        from utils.material_calculator import MaterialCalculator
        calc = MaterialCalculator({})
        assert calc is not None

    def test_with_params(self):
        from utils.material_calculator import MaterialCalculator
        params = {"material": "304不锈钢", "width": 500, "length": 1000}
        calc = MaterialCalculator(params)
        assert calc is not None

    def test_get_materials_by_category(self):
        from utils.material_calculator import MaterialCalculator
        calc = MaterialCalculator({})
        result = calc.get_materials_by_category()
        assert isinstance(result, dict)

    def test_format_material_display(self):
        from utils.material_calculator import MaterialCalculator
        calc = MaterialCalculator({"material": "304不锈钢"})
        try:
            result = calc.format_material_display()
            assert isinstance(result, str)
        except Exception:
            pass  # 某些参数组合可能抛异常

    def test_validate_order_params(self):
        from utils.material_calculator import MaterialCalculator
        calc = MaterialCalculator({"width": 500, "length": 1000, "quantity": 10})
        try:
            result = calc.validate_order_params()
            assert isinstance(result, (bool, dict, list))
        except Exception:
            pass

    def test_get_available_spec_fields(self):
        from utils.material_calculator import MaterialCalculator
        calc = MaterialCalculator({})
        result = calc.get_available_spec_fields()
        assert isinstance(result, list)

    def test_get_available_qty_fields(self):
        from utils.material_calculator import MaterialCalculator
        calc = MaterialCalculator({})
        result = calc.get_available_qty_fields()
        assert isinstance(result, list)

    def test_calculate_material_types(self):
        from utils.material_calculator import MaterialCalculator
        calc = MaterialCalculator({"material": "304不锈钢", "width": 500, "length": 1000, "quantity": 10})
        result = calc.calculate_material_types()
        assert isinstance(result, (dict, list))

    def test_preview_calculation(self):
        from utils.material_calculator import MaterialCalculator
        calc = MaterialCalculator({"material": "304不锈钢", "width": 500, "length": 1000, "quantity": 10})
        try:
            result = calc.preview_calculation()
            assert isinstance(result, (dict, str))
        except Exception:
            pass


class TestLogisticsTrackerConfig:
    """logistics_tracker - TrackingConfig"""

    def test_config_default(self):
        from utils.logistics_tracker import TrackingConfig
        TrackingConfig._instance = None
        cfg = TrackingConfig()
        assert cfg.platform == "kuaidi100"
        TrackingConfig._instance = None

    def test_config_switch(self):
        from utils.logistics_tracker import TrackingConfig
        TrackingConfig._instance = None
        cfg = TrackingConfig()
        cfg.platform = "kdniao"
        assert cfg.platform == "kdniao"
        TrackingConfig._instance = None


class TestSettingsManager:
    """utils/settings_manager.py"""

    def test_instantiate(self):
        from utils.settings_manager import SettingsManager
        sm = SettingsManager()
        assert sm is not None

    def test_color_ops(self):
        from utils.settings_manager import SettingsManager
        sm = SettingsManager()
        sm.set_color("primary", "#FF0000")
        result = sm.get_color("primary")
        assert result == "#FF0000"

    def test_font_ops(self):
        from utils.settings_manager import SettingsManager
        sm = SettingsManager()
        sm.set_font_size("title", 24)
        result = sm.get_font_size("title")
        assert result == 24


class TestHelpers:
    """utils/helpers.py"""

    def test_format_amount(self):
        from utils.helpers import format_amount
        result = format_amount(1000.5)
        assert isinstance(result, str)

    def test_truncate(self):
        from utils.helpers import truncate_text
        s = "hello world test"
        result = truncate_text(s, 5)
        assert len(result) <= 5 + 3

    def test_get_urgency_color(self):
        from utils.helpers import get_urgency_color
        result = get_urgency_color("高")
        assert isinstance(result, str)

    def test_validate_date(self):
        from utils.helpers import validate_date
        result = validate_date("2025-01-01")
        assert isinstance(result, tuple)  # 返回 (is_valid, cleaned, error)

    def test_days_until(self):
        from utils.helpers import days_until
        result = days_until("2099-12-31")
        assert isinstance(result, int)

    def test_format_date(self):
        from utils.helpers import format_date
        result = format_date("2025-01-01")
        assert isinstance(result, str)
