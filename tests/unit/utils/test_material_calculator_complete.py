# -*- coding: utf-8 -*-
"""
utils/material_calculator.py 测试 - 当前54%，提升到80%+
"""
import pytest
from unittest.mock import patch, MagicMock


class TestMaterialCalculatorTokenize:
    """tokenize 函数测试 - 覆盖 L40-55"""

    def test_simple_number(self):
        from utils.material_calculator import tokenize
        tokens = tokenize("123")
        assert tokens == [('NUM', 123.0)]

    def test_decimal_number(self):
        from utils.material_calculator import tokenize
        tokens = tokenize("12.5")
        assert tokens == [('NUM', 12.5)]

    def test_addition(self):
        from utils.material_calculator import tokenize
        tokens = tokenize("10+5")
        assert ('OP', '+') in tokens
        assert ('NUM', 10.0) in tokens
        assert ('NUM', 5.0) in tokens

    def test_complex_expression(self):
        from utils.material_calculator import tokenize
        tokens = tokenize("10+5*2-3")
        op_count = sum(1 for t in tokens if t[0] == 'OP')
        num_count = sum(1 for t in tokens if t[0] == 'NUM')
        assert op_count == 3
        assert num_count == 4

    def test_parentheses(self):
        from utils.material_calculator import tokenize
        tokens = tokenize("(10+5)")
        assert ('OP', '(') in tokens
        assert ('OP', ')') in tokens

    def test_spaces_ignored(self):
        from utils.material_calculator import tokenize
        tokens = tokenize("10 + 5 * 2")
        # 空格被忽略，所以只有 5 个 token: NUM(10) OP(+) NUM(5) OP(*) NUM(2)
        assert len(tokens) == 5
        assert ('NUM', 10.0) in tokens
        assert ('OP', '+') in tokens


class TestMaterialCalculatorEvaluate:
    """evaluate 函数测试 - 覆盖 L57-93"""

    def test_simple_addition(self):
        from utils.material_calculator import evaluate, tokenize
        tokens = tokenize("10+5")
        result = evaluate(tokens)
        assert result == 15.0

    def test_multiplication(self):
        from utils.material_calculator import evaluate, tokenize
        tokens = tokenize("3*4")
        result = evaluate(tokens)
        assert result == 12.0

    def test_division(self):
        from utils.material_calculator import evaluate, tokenize
        tokens = tokenize("10/2")
        result = evaluate(tokens)
        assert result == 5.0

    def test_order_of_operations(self):
        from utils.material_calculator import evaluate, tokenize
        # 2 + 3 * 4 = 14 (not 20)
        tokens = tokenize("2+3*4")
        result = evaluate(tokens)
        assert result == 14.0

    def test_parentheses_override(self):
        from utils.material_calculator import evaluate, tokenize
        # (2 + 3) * 4 = 20
        tokens = tokenize("(2+3)*4")
        result = evaluate(tokens)
        assert result == 20.0

    def test_empty_tokens(self):
        from utils.material_calculator import evaluate
        result = evaluate([])
        assert result == 0.0


class TestSafeEvalFormula:
    """safe_eval_formula 函数测试 - 覆盖 L22-38"""

    def test_empty_formula(self):
        from utils.material_calculator import safe_eval_formula
        assert safe_eval_formula("") == 0.0

    def test_valid_formula(self):
        from utils.material_calculator import safe_eval_formula
        assert safe_eval_formula("10+5") == 15.0

    def test_invalid_chars_raise(self):
        from utils.material_calculator import safe_eval_formula
        # 包含非法字符时抛出 ValueError
        with pytest.raises(ValueError, match="非法字符"):
            safe_eval_formula("10+print(1)")

    def test_chinese_chars_replaced(self):
        from utils.material_calculator import safe_eval_formula
        # × 和 ÷ 应被替换
        assert safe_eval_formula("10×5") == 50.0
        assert safe_eval_formula("10÷2") == 5.0


class TestMaterialCalculatorAutoBrace:
    """_auto_brace_params 测试 - 覆盖 L226-259"""

    def test_empty_string(self):
        from utils.material_calculator import MaterialCalculator
        calc = MaterialCalculator({})
        result = calc._auto_brace_params("")
        assert result == ""

    def test_chinese_word(self):
        from utils.material_calculator import MaterialCalculator
        calc = MaterialCalculator({})
        result = calc._auto_brace_params("直径10长度5")
        # 直径和长度在排除列表中，不加花括号
        assert "直径" in result
        assert "长度" in result

    def test_existing_braces_preserved(self):
        from utils.material_calculator import MaterialCalculator
        calc = MaterialCalculator({})
        result = calc._auto_brace_params("{直径}")
        assert "{直径}" in result


class TestMaterialCalculatorPreview:
    """preview_calculation 测试"""

    @patch('utils.material_calculator.MaterialRulesDAO')
    def test_preview_calculation(self, mock_dao):
        mock_dao.get_by_product_type.return_value = []

        from utils.material_calculator import MaterialCalculator
        result = MaterialCalculator.preview_calculation("重型", {
            "product_type": "重型",
            "quantity": 100
        })
        assert "product_type" in result
        assert "materials" in result


class TestMaterialCalculatorSpecFields:
    """可选规格字段测试"""

    def test_get_available_spec_fields(self):
        from utils.material_calculator import MaterialCalculator
        fields = MaterialCalculator.get_available_spec_fields()
        assert len(fields) > 0
        assert all("key" in f for f in fields)

    def test_get_available_qty_fields(self):
        from utils.material_calculator import MaterialCalculator
        fields = MaterialCalculator.get_available_qty_fields()
        assert len(fields) > 0
        assert any(f["key"] == "quantity" for f in fields)

    def test_get_material_params_for_product(self):
        from utils.material_calculator import MaterialCalculator
        params = MaterialCalculator.get_material_params_for_product("重型")
        assert isinstance(params, list)


class TestMaterialCalculatorFormat:
    """format_material_display 测试"""

    def test_with_spec(self):
        from utils.material_calculator import MaterialCalculator
        mat = {"material_name": "不锈钢网丝", "spec_value": "2.0", "spec_unit": "mm"}
        result = MaterialCalculator.format_material_display(mat)
        assert "不锈钢网丝" in result
        assert "2.0" in result

    def test_without_spec(self):
        from utils.material_calculator import MaterialCalculator
        mat = {"material_name": "不锈钢网丝"}
        result = MaterialCalculator.format_material_display(mat)
        assert result == "不锈钢网丝"


class TestGetMaterialsByCategory:
    """get_materials_by_category 测试 - 覆盖 L261-278"""

    def test_material_params_and_dimension_params(self):
        """material_param 在 MATERIAL_FIELDS 中的归 material_params，之外的归 dimension_params"""
        from utils.material_calculator import MaterialCalculator

        calc = MaterialCalculator({
            "product_type": "重型",
            "曲轴材质": "45#钢",
            "挡板材质": "Q235",
            "quantity": 100
        })

        # 模拟 calculate_material_types 返回混合数据：
        # - "曲轴材质" 和 "挡板材质" 在 MATERIAL_FIELDS 中 → material_params
        # - "自定义材质" 不在 MATERIAL_FIELDS 中 → dimension_params
        calc.calculate_material_types = lambda: [
            {"material_param": "曲轴材质", "material_name": "45#钢曲轴"},
            {"material_param": "挡板材质", "material_name": "Q235挡板"},
            {"material_param": "自定义材质", "material_name": "自定义件"},
            {"material_param": "其他参数", "material_name": "其他件"},
        ]

        result = calc.get_materials_by_category()

        assert "material_params" in result
        assert "dimension_params" in result

        # 检查分类
        material_params_names = {m["material_name"] for m in result["material_params"]}
        dimension_params_names = {m["material_name"] for m in result["dimension_params"]}

        assert "45#钢曲轴" in material_params_names
        assert "Q235挡板" in material_params_names
        assert "自定义件" in dimension_params_names
        assert "其他件" in dimension_params_names

        assert len(result["material_params"]) == 2
        assert len(result["dimension_params"]) == 2


class TestMaterialCalculatorValidate:
    """validate_order_params 测试"""

    def test_valid_params(self):
        from utils.material_calculator import MaterialCalculator
        ok, errors = MaterialCalculator.validate_order_params({
            "product_type": "重型",
            "quantity": 100
        })
        assert ok is True
        assert len(errors) == 0

    def test_missing_product_type(self):
        from utils.material_calculator import MaterialCalculator
        ok, errors = MaterialCalculator.validate_order_params({
            "quantity": 100
        })
        assert ok is False
        assert any("产品类型" in e for e in errors)

    def test_missing_quantity(self):
        from utils.material_calculator import MaterialCalculator
        ok, errors = MaterialCalculator.validate_order_params({
            "product_type": "重型"
        })
        assert ok is False
        assert any("数量" in e for e in errors)


class TestCalculateMaterialTypesWithRules:
    """calculate_material_types 规则分支测试 - 覆盖 L116-176"""

    @patch("utils.material_calculator.MaterialRulesDAO.get_by_product_type")
    def test_rule_with_spec_field_and_qty_formula(self, mock_get_rules):
        """规则: spec_field + qty_formula 同时存在"""
        mock_get_rules.return_value = [
            {
                "material_param": "网丝材质",
                "spec_field": "钢丝直径",
                "spec_unit": "mm",
                "qty_formula": "{qty}*2",
                "qty_field": "quantity",
                "qty_unit": "米"
            }
        ]
        from utils.material_calculator import MaterialCalculator
        calc = MaterialCalculator({
            "product_type": "网带",
            "quantity": 10,
            "qty": 10,          # 代码检查 {qty} 占位符在 order_params 中
            "网丝材质": "304不锈钢",
            "钢丝直径": 2.0,
        })
        result = calc.calculate_material_types()
        assert len(result) >= 1
        mat = next(m for m in result if m["material_param"] == "网丝材质")
        assert mat["material_name"] == "304不锈钢网丝"
        assert mat["spec_value"] == "2.0"
        assert mat["spec_unit"] == "mm"
        assert mat["qty_value"] == 20.0  # 10 * 2
        assert mat["rule_enabled"] is True
        assert mat["missing_params"] == []

    @patch("utils.material_calculator.MaterialRulesDAO.get_by_product_type")
    def test_rule_spec_field_missing_in_order_params(self, mock_get_rules):
        """规则: spec_field 在 order_params 中缺失 -> missing_params"""
        mock_get_rules.return_value = [
            {
                "material_param": "网丝材质",
                "spec_field": "钢丝直径",
                "spec_unit": "mm",
                "qty_formula": "{qty}*2",
                "qty_field": "quantity",
            }
        ]
        from utils.material_calculator import MaterialCalculator
        calc = MaterialCalculator({
            "product_type": "网带",
            "quantity": 10,
            "qty": 10,
            "网丝材质": "304不锈钢",
        })
        result = calc.calculate_material_types()
        mat = next(m for m in result if m["material_param"] == "网丝材质")
        assert mat["spec_value"] is None
        assert "规格字段「钢丝直径」" in mat["missing_params"]
        # 注意: spec_field 缺失不影响 qty_formula 计算（独立分支）
        # qty 在 order_params 中, 所以 qty_formula 仍被计算
        assert mat["qty_value"] == 20.0

    @patch("utils.material_calculator.MaterialRulesDAO.get_by_product_type")
    def test_rule_with_qty_field_no_formula(self, mock_get_rules):
        """规则: qty_field 存在但无 qty_formula -> 直接取 order_params 值"""
        mock_get_rules.return_value = [
            {
                "material_param": "网丝材质",
                "qty_field": "quantity",
                "qty_unit": "千克",
            }
        ]
        from utils.material_calculator import MaterialCalculator
        calc = MaterialCalculator({
            "product_type": "网带",
            "quantity": 50,
            "网丝材质": "304不锈钢",
        })
        result = calc.calculate_material_types()
        mat = next(m for m in result if m["material_param"] == "网丝材质")
        assert mat["qty_value"] == 50.0
        assert mat["qty_unit"] == "千克"
        assert mat["rule_enabled"] is True

    @patch("utils.material_calculator.MaterialRulesDAO.get_by_product_type")
    def test_rule_with_spec_unit_override(self, mock_get_rules):
        """规则: spec_unit 覆盖默认单位"""
        mock_get_rules.return_value = [
            {
                "material_param": "网丝材质",
                "spec_field": "钢丝直径",
                "spec_unit": "cm",
                "qty_field": "quantity",
            }
        ]
        from utils.material_calculator import MaterialCalculator
        calc = MaterialCalculator({
            "product_type": "网带",
            "quantity": 10,
            "网丝材质": "304不锈钢",
            "钢丝直径": 2.0,
        })
        result = calc.calculate_material_types()
        mat = next(m for m in result if m["material_param"] == "网丝材质")
        assert mat["spec_value"] == "2.0"
        assert mat["spec_unit"] == "cm"

    @patch("utils.material_calculator.MaterialRulesDAO.get_by_product_type")
    def test_rule_spec_field_no_rule_spec_unit(self, mock_get_rules):
        """规则: spec_field 存在但 rule 无 spec_unit -> 从 DIM_FIELDS 查找 unit"""
        mock_get_rules.return_value = [
            {
                "material_param": "网丝材质",
                "spec_field": "钢丝直径",
                "qty_field": "quantity",
            }
        ]
        from utils.material_calculator import MaterialCalculator
        calc = MaterialCalculator({
            "product_type": "网带",
            "quantity": 10,
            "网丝材质": "304不锈钢",
            "钢丝直径": 2.0,
        })
        result = calc.calculate_material_types()
        mat = next(m for m in result if m["material_param"] == "网丝材质")
        assert mat["spec_value"] == "2.0"
        assert mat["spec_unit"] == "mm"  # 来自 DIM_FIELDS

    @patch("utils.material_calculator.MaterialRulesDAO.get_by_product_type")
    def test_no_rule_for_material(self, mock_get_rules):
        """材质无对应规则 -> rule_enabled=False, 不计算 spec/qty"""
        mock_get_rules.return_value = []
        from utils.material_calculator import MaterialCalculator
        calc = MaterialCalculator({
            "product_type": "网带",
            "quantity": 10,
            "网丝材质": "304不锈钢",
        })
        result = calc.calculate_material_types()
        mat = next(m for m in result if m["material_param"] == "网丝材质")
        assert mat["rule_enabled"] is False
        assert mat["spec_value"] is None
        assert mat["spec_unit"] == ""
        assert mat["qty_value"] is None


class TestCalculateQtyFormulas:
    """_calculate_qty 公式填充测试 - 覆盖 L182-224"""

    @patch("utils.material_calculator.MaterialRulesDAO.get_by_product_type")
    def test_qty_placeholder_replacement(self, mock_get_rules):
        """{qty} 占位符替换"""
        mock_get_rules.return_value = [
            {
                "material_param": "网丝材质",
                "qty_formula": "{qty}*2",
                "qty_field": "quantity",
            }
        ]
        from utils.material_calculator import MaterialCalculator
        calc = MaterialCalculator({
            "product_type": "网带",
            "quantity": 10,
            "qty": 10,
            "网丝材质": "304不锈钢",
        })
        result = calc.calculate_material_types()
        mat = next(m for m in result if m["material_param"] == "网丝材质")
        assert mat["qty_value"] == 20.0

    @patch("utils.material_calculator.MaterialRulesDAO.get_by_product_type")
    def test_density_placeholder_replacement(self, mock_get_rules):
        """材质密度占位符替换: {网丝材质} -> 7930 (304不锈钢密度)"""
        mock_get_rules.return_value = [
            {
                "material_param": "网丝材质",
                "qty_formula": "{qty}*{网丝材质}",
                "qty_field": "quantity",
            }
        ]
        from utils.material_calculator import MaterialCalculator
        calc = MaterialCalculator({
            "product_type": "网带",
            "quantity": 10,
            "qty": 10,
            "网丝材质": "304不锈钢",
        })
        result = calc.calculate_material_types()
        mat = next(m for m in result if m["material_param"] == "网丝材质")
        assert mat["qty_value"] == 79300.0

    @patch("utils.material_calculator.MaterialRulesDAO.get_by_product_type")
    def test_placeholder_order_param(self, mock_get_rules):
        """order param key 占位符替换: {总宽} -> 1000"""
        mock_get_rules.return_value = [
            {
                "material_param": "网丝材质",
                "qty_formula": "{qty}*{总宽}",
                "qty_field": "quantity",
            }
        ]
        from utils.material_calculator import MaterialCalculator
        calc = MaterialCalculator({
            "product_type": "网带",
            "quantity": 10,
            "qty": 10,
            "网丝材质": "304不锈钢",
            "总宽": 1000,
        })
        result = calc.calculate_material_types()
        mat = next(m for m in result if m["material_param"] == "网丝材质")
        assert mat["qty_value"] == 10000.0

    @patch("utils.material_calculator.MaterialRulesDAO.get_by_product_type")
    def test_raw_param_key_replacement(self, mock_get_rules):
        """order_params key 直接替换 (无花括号)"""
        mock_get_rules.return_value = [
            {
                "material_param": "网丝材质",
                "qty_formula": "{qty}*总宽",
                "qty_field": "quantity",
            }
        ]
        from utils.material_calculator import MaterialCalculator
        calc = MaterialCalculator({
            "product_type": "网带",
            "quantity": 10,
            "qty": 10,
            "网丝材质": "304不锈钢",
            "总宽": 1000,
        })
        result = calc.calculate_material_types()
        mat = next(m for m in result if m["material_param"] == "网丝材质")
        assert mat["qty_value"] == 10000.0

    @patch("utils.material_calculator.MaterialRulesDAO.get_by_product_type")
    def test_density_literal_in_formula(self, mock_get_rules):
        """公式中的"密度"字面量 -> 替换为材质密度值"""
        mock_get_rules.return_value = [
            {
                "material_param": "网丝材质",
                "qty_formula": "{qty}*密度",
                "qty_field": "quantity",
            }
        ]
        from utils.material_calculator import MaterialCalculator
        calc = MaterialCalculator({
            "product_type": "网带",
            "quantity": 10,
            "qty": 10,
            "网丝材质": "304不锈钢",
        })
        result = calc.calculate_material_types()
        mat = next(m for m in result if m["material_param"] == "网丝材质")
        assert mat["qty_value"] == 79300.0

    @patch("utils.material_calculator.MaterialRulesDAO.get_by_product_type")
    def test_safe_eval_formula_path_with_parentheses(self, mock_get_rules):
        """safe_eval_formula 路径: 带括号的复杂公式"""
        mock_get_rules.return_value = [
            {
                "material_param": "网丝材质",
                "qty_formula": "{qty}*(2+3)",
                "qty_field": "quantity",
            }
        ]
        from utils.material_calculator import MaterialCalculator
        calc = MaterialCalculator({
            "product_type": "网带",
            "quantity": 10,
            "qty": 10,
            "网丝材质": "304不锈钢",
        })
        result = calc.calculate_material_types()
        mat = next(m for m in result if m["material_param"] == "网丝材质")
        assert mat["qty_value"] == 50.0

    @patch("utils.material_calculator.MaterialRulesDAO.get_by_product_type")
    def test_qty_formula_with_missing_placeholder(self, mock_get_rules):
        """公式占位符在 order_params 中缺失 -> missing_params, qty_value=None"""
        mock_get_rules.return_value = [
            {
                "material_param": "网丝材质",
                "qty_formula": "{qty}*{缺失字段}",
                "qty_field": "quantity",
            }
        ]
        from utils.material_calculator import MaterialCalculator
        calc = MaterialCalculator({
            "product_type": "网带",
            "quantity": 10,
            "qty": 10,
            "网丝材质": "304不锈钢",
        })
        result = calc.calculate_material_types()
        mat = next(m for m in result if m["material_param"] == "网丝材质")
        # {qty} 在 order_params 中 (qty:10), 但 {缺失字段} 不在
        assert "「缺失字段」" in mat["missing_params"]
        assert mat["qty_value"] is None


class TestAutoBraceParamsEdgeCases:
    """_auto_brace_params 边界情况测试 - 覆盖 L239, L251"""

    def test_nested_braces(self):
        """嵌套花括号 {{test}} -> depth 跟踪正确"""
        from utils.material_calculator import MaterialCalculator
        calc = MaterialCalculator({})
        result = calc._auto_brace_params("{{test}}")
        assert result == "{{test}}"

    def test_custom_chinese_param_not_in_exclusion(self):
        """自定义中文参数(>=2字,不在排除列表) -> 添加花括号"""
        from utils.material_calculator import MaterialCalculator
        calc = MaterialCalculator({})
        result = calc._auto_brace_params("自定义参数")
        assert result == "{自定义参数}"

    def test_chinese_params_in_exclusion_list(self):
        """连续中文被视为一个整体 -> 整体加花括号"""
        from utils.material_calculator import MaterialCalculator
        calc = MaterialCalculator({})
        result = calc._auto_brace_params("宽度加厚度")
        # 整个"宽度加厚度"是连续中文, 不在排除列表中 -> 整体加花括号
        assert result == "{宽度加厚度}"

    def test_density_in_exclusion_list(self):
        """排除列表中的"密度"(2字) -> 不加花括号"""
        from utils.material_calculator import MaterialCalculator
        calc = MaterialCalculator({})
        result = calc._auto_brace_params("密度")
        assert result == "密度"

    def test_single_chinese_char_no_brace(self):
        """单字符中文 -> 不加花括号"""
        from utils.material_calculator import MaterialCalculator
        calc = MaterialCalculator({})
        result = calc._auto_brace_params("大")
        assert result == "大"

    def test_mixed_chinese_and_operators(self):
        """中文与运算符混合"""
        from utils.material_calculator import MaterialCalculator
        calc = MaterialCalculator({})
        result = calc._auto_brace_params("自定义*2")
        assert "{自定义}" in result
        assert result == "{自定义}*2"
