# -*- coding: utf-8 -*-
"""订单校验器单元测试——避免tkinter依赖"""
import pytest
import sys
import os

# 直接import模块文件，跳过desktop.views的tkinter链
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _load_validator():
    """绕过tkinter依赖直接加载校验模块"""
    path = os.path.join(PROJECT_ROOT, "desktop", "views", "validators", "order_form_validator.py")
    import importlib.util
    spec = importlib.util.spec_from_file_location("order_form_validator", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.validate_order_form


validate_order_form = _load_validator()


class TestValidateOrderForm:
    def test_valid_order(self):
        is_valid, errors = validate_order_form({
            "customer_name": "测试客户", "product_type": "网带", "quantity": 10
        })
        assert is_valid is True

    def test_missing_customer(self):
        is_valid, errors = validate_order_form({"product_type": "X", "quantity": 1})
        assert is_valid is False

    def test_missing_product(self):
        is_valid, errors = validate_order_form({"customer_name": "X", "quantity": 1})
        assert is_valid is False

    def test_zero_quantity(self):
        is_valid, _ = validate_order_form({"customer_name": "X", "product_type": "X", "quantity": 0})
        assert is_valid is False

    def test_negative_price(self):
        is_valid, _ = validate_order_form({"customer_name": "X", "product_type": "X", "quantity": 1, "unit_price": -100})
        assert is_valid is False

    def test_string_quantity(self):
        is_valid, _ = validate_order_form({"customer_name": "X", "product_type": "X", "quantity": "abc"})
        assert is_valid is False

    def test_empty_data(self):
        is_valid, errors = validate_order_form({})
        assert is_valid is False
        assert len(errors) >= 2
