# -*- coding: utf-8 -*-
"""utils/material_calculator.py 纯逻辑测试"""
import pytest
from unittest.mock import MagicMock, patch


# ============================================================
# tokenize
# ============================================================
class TestTokenize:
    def test_simple_addition(self):
        from utils.material_calculator import tokenize
        tokens = tokenize("1 + 2")
        assert tokens == [('NUM', 1.0), ('OP', '+'), ('NUM', 2.0)]

    def test_multiplication(self):
        from utils.material_calculator import tokenize
        tokens = tokenize("3 * 4")
        assert tokens == [('NUM', 3.0), ('OP', '*'), ('NUM', 4.0)]

    def test_parentheses(self):
        from utils.material_calculator import tokenize
        tokens = tokenize("(1 + 2) * 3")
        assert tokens == [
            ('OP', '('), ('NUM', 1.0), ('OP', '+'), ('NUM', 2.0), ('OP', ')'),
            ('OP', '*'), ('NUM', 3.0)
        ]

    def test_decimal(self):
        from utils.material_calculator import tokenize
        tokens = tokenize("3.14 * 2")
        assert tokens == [('NUM', 3.14), ('OP', '*'), ('NUM', 2.0)]

    def test_empty(self):
        from utils.material_calculator import tokenize
        assert tokenize("") == []

    def test_spaces_ignored(self):
        from utils.material_calculator import tokenize
        tokens = tokenize("  5  +  3  ")
        assert tokens == [('NUM', 5.0), ('OP', '+'), ('NUM', 3.0)]


# ============================================================
# evaluate (逆波兰求值)
# ============================================================
class TestEvaluate:
    def test_simple_addition(self):
        from utils.material_calculator import evaluate
        tokens = [('NUM', 1.0), ('OP', '+'), ('NUM', 2.0)]
        assert evaluate(tokens) == 3.0

    def test_multiplication(self):
        from utils.material_calculator import evaluate
        tokens = [('NUM', 3.0), ('OP', '*'), ('NUM', 4.0)]
        assert evaluate(tokens) == 12.0

    def test_precedence(self):
        from utils.material_calculator import evaluate
        tokens = [('NUM', 1.0), ('OP', '+'), ('NUM', 2.0), ('OP', '*'), ('NUM', 3.0)]
        assert evaluate(tokens) == 7.0  # 1 + (2 * 3)

    def test_parentheses(self):
        from utils.material_calculator import evaluate
        tokens = [
            ('OP', '('), ('NUM', 1.0), ('OP', '+'), ('NUM', 2.0), ('OP', ')'),
            ('OP', '*'), ('NUM', 3.0)
        ]
        assert evaluate(tokens) == 9.0  # (1 + 2) * 3

    def test_division(self):
        from utils.material_calculator import evaluate
        tokens = [('NUM', 10.0), ('OP', '/'), ('NUM', 3.0)]
        assert evaluate(tokens) == 10.0 / 3.0

    def test_empty_tokens(self):
        from utils.material_calculator import evaluate
        assert evaluate([]) == 0.0

    def test_complex_expression(self):
        from utils.material_calculator import evaluate
        # 2 + 3 * 4 - 5
        tokens = [
            ('NUM', 2.0), ('OP', '+'), ('NUM', 3.0), ('OP', '*'),
            ('NUM', 4.0), ('OP', '-'), ('NUM', 5.0)
        ]
        assert evaluate(tokens) == 9.0  # 2 + 12 - 5


# ============================================================
# safe_eval_formula
# ============================================================
class TestSafeEvalFormula:
    def test_simple(self):
        from utils.material_calculator import safe_eval_formula
        assert safe_eval_formula("1 + 2") == 3.0

    def test_chinese_mult(self):
        from utils.material_calculator import safe_eval_formula
        assert safe_eval_formula("3 × 4") == 12.0

    def test_chinese_div(self):
        from utils.material_calculator import safe_eval_formula
        assert safe_eval_formula("8 ÷ 2") == 4.0

    def test_upper_X(self):
        from utils.material_calculator import safe_eval_formula
        assert safe_eval_formula("3 X 4") == 12.0

    def test_empty_returns_zero(self):
        from utils.material_calculator import safe_eval_formula
        assert safe_eval_formula("") == 0.0

    def test_illegal_char_raises(self):
        from utils.material_calculator import safe_eval_formula
        with pytest.raises(ValueError):
            safe_eval_formula("1 + abc")

    def test_invalid_expr_returns_zero(self):
        from utils.material_calculator import safe_eval_formula
        # only numbers count - e.g., "") is empty, let me test "()"
        assert safe_eval_formula("()") == 0.0


# ============================================================
# MaterialCalculator static methods
# ============================================================
class TestFormatMaterialDisplay:
    def test_with_spec(self):
        from utils.material_calculator import MaterialCalculator
        m = {"material_name": "不锈钢网丝", "spec_value": "2.0", "spec_unit": "mm"}
        assert MaterialCalculator.format_material_display(m) == "不锈钢网丝（2.0mm）"

    def test_without_spec(self):
        from utils.material_calculator import MaterialCalculator
        m = {"material_name": "不锈钢网丝"}
        assert MaterialCalculator.format_material_display(m) == "不锈钢网丝"

    def test_none_spec(self):
        from utils.material_calculator import MaterialCalculator
        m = {"material_name": "钢丝", "spec_value": None}
        assert MaterialCalculator.format_material_display(m) == "钢丝"


class TestValidateOrderParams:
    def test_valid(self):
        from utils.material_calculator import MaterialCalculator
        ok, errors = MaterialCalculator.validate_order_params({
            "product_type": "平网",
            "quantity": 100
        })
        assert ok is True
        assert errors == []

    def test_missing_product_type(self):
        from utils.material_calculator import MaterialCalculator
        ok, errors = MaterialCalculator.validate_order_params({"quantity": 100})
        assert ok is False
        assert "产品类型不能为空" in errors

    def test_missing_quantity(self):
        from utils.material_calculator import MaterialCalculator
        ok, errors = MaterialCalculator.validate_order_params({"product_type": "平网"})
        assert ok is False
        assert "数量不能为空" in errors

    def test_both_missing(self):
        from utils.material_calculator import MaterialCalculator
        ok, errors = MaterialCalculator.validate_order_params({})
        assert ok is False
        assert len(errors) == 2


class TestGetAvailableSpecFields:
    def test_returns_list(self):
        from utils.material_calculator import MaterialCalculator
        fields = MaterialCalculator.get_available_spec_fields()
        assert isinstance(fields, list)
        assert len(fields) > 0
        for f in fields:
            assert "key" in f
            assert "label" in f


class TestGetAvailableQtyFields:
    def test_returns_list_with_quantity(self):
        from utils.material_calculator import MaterialCalculator
        fields = MaterialCalculator.get_available_qty_fields()
        assert isinstance(fields, list)
        keys = [f["key"] for f in fields]
        assert "quantity" in keys


# ============================================================
# _auto_brace_params
# ============================================================
class TestAutoBraceParams:
    def test_no_chinese_unchanged(self):
        from utils.material_calculator import MaterialCalculator
        mc = MaterialCalculator({})
        result = mc._auto_brace_params("2 * 3")
        assert result == "2 * 3"

    def test_empty_string(self):
        from utils.material_calculator import MaterialCalculator
        mc = MaterialCalculator({})
        assert mc._auto_brace_params("") == ""
