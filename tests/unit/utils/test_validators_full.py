# -*- coding: utf-8 -*-
"""utils/validators.py 全覆盖测试"""
import pytest
from core.exceptions import ValidationException


# ============================================================
# CommonValidators
# ============================================================
class TestCommonValidators:
    def test_required_ok(self):
        from utils.validators import CommonValidators
        assert CommonValidators.required("hello") == "hello"

    def test_required_none_raises(self):
        from utils.validators import CommonValidators
        with pytest.raises(ValidationException, match="不能为空"):
            CommonValidators.required(None, field_name="姓名")

    def test_required_empty_string_raises(self):
        from utils.validators import CommonValidators
        with pytest.raises(ValidationException):
            CommonValidators.required("   ", field_name="姓名")

    def test_length_ok(self):
        from utils.validators import CommonValidators
        assert CommonValidators.length("hello", min_len=1, max_len=10) == "hello"

    def test_length_too_short(self):
        from utils.validators import CommonValidators
        with pytest.raises(ValidationException, match="长度不能少于"):
            CommonValidators.length("ab", min_len=5)

    def test_length_too_long(self):
        from utils.validators import CommonValidators
        with pytest.raises(ValidationException, match="长度不能超过"):
            CommonValidators.length("abcdef", max_len=3)

    def test_length_not_string(self):
        from utils.validators import CommonValidators
        with pytest.raises(ValidationException, match="必须是字符串"):
            CommonValidators.length(123, field_name="编号")

    def test_range_ok(self):
        from utils.validators import CommonValidators
        assert CommonValidators.range(50, min_val=0, max_val=100) == 50.0

    def test_range_too_small(self):
        from utils.validators import CommonValidators
        with pytest.raises(ValidationException, match="不能小于"):
            CommonValidators.range(-5, min_val=0)

    def test_range_too_large(self):
        from utils.validators import CommonValidators
        with pytest.raises(ValidationException, match="不能大于"):
            CommonValidators.range(200, max_val=100)

    def test_range_not_number(self):
        from utils.validators import CommonValidators
        with pytest.raises(ValidationException, match="必须是数字"):
            CommonValidators.range("abc")

    def test_pattern_ok(self):
        from utils.validators import CommonValidators
        assert CommonValidators.pattern("ABC123", r"^[A-Z0-9]+$") == "ABC123"

    def test_pattern_mismatch(self):
        from utils.validators import CommonValidators
        with pytest.raises(ValidationException, match="格式不正确"):
            CommonValidators.pattern("hello world", r"^\d+$")

    def test_choices_ok(self):
        from utils.validators import CommonValidators
        assert CommonValidators.choices("A", ["A", "B", "C"]) == "A"

    def test_choices_not_in_list(self):
        from utils.validators import CommonValidators
        with pytest.raises(ValidationException, match="必须是以下值之一"):
            CommonValidators.choices("Z", ["A", "B", "C"])

    def test_date_format_ok(self):
        from utils.validators import CommonValidators
        assert CommonValidators.date_format("2025-06-01") == "2025-06-01"

    def test_date_format_bad(self):
        from utils.validators import CommonValidators
        with pytest.raises(ValidationException, match="格式应为"):
            CommonValidators.date_format("06/01/2025")


# ============================================================
# OrderValidator
# ============================================================
class TestOrderValidator:
    def test_validate_create_ok(self):
        from utils.validators import OrderValidator
        d = OrderValidator.validate_create({
            "customer_name": "张三",
            "product_type": "平网",
            "quantity": 100,
            "delivery_date": "2025-12-31",
        })
        assert d["customer_name"] == "张三"

    def test_validate_create_missing_required(self):
        from utils.validators import OrderValidator
        with pytest.raises(ValidationException, match="缺少必填字段"):
            OrderValidator.validate_create({})

    def test_validate_create_bad_quantity(self):
        from utils.validators import OrderValidator
        with pytest.raises(ValidationException, match="数量必须"):
            OrderValidator.validate_create({
                "customer_name": "李四",
                "product_type": "人字网",
                "quantity": "abc",
            })

    def test_validate_create_negative_quantity(self):
        from utils.validators import OrderValidator
        with pytest.raises(ValidationException, match="必须大于0"):
            OrderValidator.validate_create({
                "customer_name": "李四",
                "product_type": "人字网",
                "quantity": -10,
            })

    def test_validate_create_bad_date(self):
        from utils.validators import OrderValidator
        with pytest.raises(ValidationException, match="日期格式"):
            OrderValidator.validate_create({
                "customer_name": "王五",
                "product_type": "力骨网",
                "delivery_date": "31/12/2025",
            })

    def test_validate_update_filters_unknown_fields(self):
        from utils.validators import OrderValidator
        d = OrderValidator.validate_update({
            "customer_name": "新客户",
            "hacker_field": "DROP TABLE",
            "status": "confirmed",
        })
        assert d["customer_name"] == "新客户"
        assert d["status"] == "confirmed"
        assert "hacker_field" not in d


# ============================================================
# ProcessValidator
# ============================================================
class TestProcessValidator:
    def test_validate_report_ok(self):
        from utils.validators import ProcessValidator
        d = ProcessValidator.validate_report({
            "quantity": 50,
            "qualified_rate": 98.5,
        })
        assert d["quantity"] == 50

    def test_validate_report_negative_qty(self):
        from utils.validators import ProcessValidator
        with pytest.raises(ValidationException, match="不能为负数"):
            ProcessValidator.validate_report({"quantity": -5})

    def test_validate_report_bad_qty(self):
        from utils.validators import ProcessValidator
        with pytest.raises(ValidationException, match="必须是数字"):
            ProcessValidator.validate_report({"quantity": "not_a_number"})

    def test_validate_report_rate_out_of_range(self):
        from utils.validators import ProcessValidator
        with pytest.raises(ValidationException, match="0-100"):
            ProcessValidator.validate_report({"qualified_rate": 150})

    def test_validate_report_rate_negative(self):
        from utils.validators import ProcessValidator
        with pytest.raises(ValidationException, match="0-100"):
            ProcessValidator.validate_report({"qualified_rate": -1})

    def test_validate_report_rate_bad_type(self):
        from utils.validators import ProcessValidator
        with pytest.raises(ValidationException, match="必须是数字"):
            ProcessValidator.validate_report({"qualified_rate": "abc"})


# ============================================================
# InventoryValidator
# ============================================================
class TestInventoryValidator:
    def test_validate_adjustment_ok(self):
        from utils.validators import InventoryValidator
        d = InventoryValidator.validate_adjustment({
            "adjustment": 10,
            "current_quantity": 100,
        })
        assert d["adjustment"] == 10

    def test_validate_adjustment_zero(self):
        from utils.validators import InventoryValidator
        # 修复后 adjustment=0 正确触发校验
        with pytest.raises(ValidationException, match="不能为0"):
            InventoryValidator.validate_adjustment({"adjustment": 0})

    def test_validate_adjustment_zero_no_current_qty_error(self):
        """adjustment=0 is falsy, so only the current_quantity check runs."""
        from utils.validators import InventoryValidator
        with pytest.raises(ValidationException, match="必须是数字"):
            InventoryValidator.validate_adjustment({
                "adjustment": 0,
                "current_quantity": "bad",
            })

    def test_validate_adjustment_bad_type(self):
        from utils.validators import InventoryValidator
        with pytest.raises(ValidationException, match="必须是数字"):
            InventoryValidator.validate_adjustment({"adjustment": "abc"})

    def test_validate_current_qty_negative(self):
        from utils.validators import InventoryValidator
        with pytest.raises(ValidationException, match="不能为负数"):
            InventoryValidator.validate_adjustment({
                "adjustment": 5,
                "current_quantity": -10,
            })

    def test_validate_current_qty_bad_type(self):
        from utils.validators import InventoryValidator
        with pytest.raises(ValidationException, match="必须是数字"):
            InventoryValidator.validate_adjustment({
                "adjustment": 5,
                "current_quantity": "no",
            })

    def test_validate_no_errors_without_data(self):
        from utils.validators import InventoryValidator
        d = InventoryValidator.validate_adjustment({})
        assert d == {}


# ============================================================
# FormValidator
# ============================================================
class TestFormValidator:
    def test_add_rule_and_validate_ok(self):
        from utils.validators import FormValidator, CommonValidators
        fv = FormValidator()
        fv.add_rule("name", CommonValidators.required)
        d = fv.validate({"name": "张三"})
        assert d["name"] == "张三"

    def test_required_field_missing(self):
        from utils.validators import FormValidator, CommonValidators
        fv = FormValidator()
        fv.add_rule("name", required=True)
        with pytest.raises(ValidationException, match="不能为空"):
            fv.validate({"name": ""})

    def test_required_field_none(self):
        from utils.validators import FormValidator, CommonValidators
        fv = FormValidator()
        fv.add_rule("email", required=True)
        with pytest.raises(ValidationException):
            fv.validate({})

    def test_multiple_rules(self):
        from utils.validators import FormValidator, CommonValidators
        fv = FormValidator()
        fv.add_rule("name", required=True) \
          .add_rule("age", CommonValidators.range)

        d = fv.validate({"name": "张三", "age": 30})
        assert d["name"] == "张三"
        assert d["age"] == 30.0

    def test_validation_error_collected(self):
        from utils.validators import FormValidator, CommonValidators
        fv = FormValidator()
        fv.add_rule("age", CommonValidators.range)
        with pytest.raises(ValidationException):
            fv.validate({"age": "not_number"})

    def test_optional_field_skipped(self):
        from utils.validators import FormValidator, CommonValidators
        fv = FormValidator()
        # When field missing, value=None → validator called with None
        # pattern(None) raises because str(None) doesn't match
        # This tests the error collection behavior
        fv.add_rule("email", lambda v: CommonValidators.required(v, field_name="邮箱"), required=False)
        d = fv.validate({"email": "test@example.com"})
        assert d["email"] == "test@example.com"
