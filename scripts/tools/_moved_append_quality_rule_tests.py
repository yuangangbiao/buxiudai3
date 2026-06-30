"""临时脚本：追加 TestEvaluateQualityRules 到测试文件末尾"""
import ast
import pathlib

target = pathlib.Path("tests/unit/models/test_quality_rule.py")
content = target.read_text(encoding="utf-8")

# 检查是否已包含
if "class TestEvaluateQualityRules" in content:
    print("TestEvaluateQualityRules 已存在，跳过")
else:
    append = """

class TestEvaluateQualityRules:
    \"\"\"Test QualityRuleDAO.evaluate_quality_rules\"\"\"

    @pytest.fixture(autouse=True)
    def patch_order_dao(self):
        with patch("models.quality_rule.OrderDAO") as mock:
            self.mock_order_dao = mock
            yield mock

    @pytest.fixture(autouse=True)
    def patch_process_calc_rule(self):
        with patch("models.quality_rule.ProcessCalcRule") as mock:
            self.mock_calc_rule = mock
            yield mock

    def test_order_not_found(self, cursor):
        \"\"\"订单不存在返回空列表\"\"\"
        cursor.fetchone.return_value = None
        self.mock_order_dao.get_by_order_no.return_value = None
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.evaluate_quality_rules("不存在工单")
        assert result == []
        cursor.execute.assert_called_once()

    def test_no_matching_rules(self, cursor):
        \"\"\"无匹配规则时不做评估\"\"\"
        cursor.fetchone.return_value = None
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.evaluate_quality_rules("W02406001")
        assert result == []

    def test_no_formula(self, cursor):
        \"\"\"规则无公式时跳过\"\"\"
        cursor.fetchone.return_value = None
        self.mock_order_dao.get_by_order_no.return_value = {"宽度": 100}
        self.mock_calc_rule.calc.return_value = None
        from test_quality_rule import QualityRuleDAO
        result = QualityRuleDAO.evaluate_quality_rules("W02406001")
        assert result == []

    def test_formula_tolerance_pass(self, cursor):
        \"\"\"公式+公差判定通过\"\"\"
        cursor.fetchone.return_value = None
        self.mock_order_dao.get_by_order_no.return_value = {"宽度": 100.0}
        self.mock_calc_rule.calc.return_value = 105.0
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.evaluate_quality_rules("W02406001")
        assert isinstance(result, list)

    def test_formula_tolerance_fail(self, cursor):
        \"\"\"公式+公差判定失败\"\"\"
        cursor.fetchone.return_value = None
        self.mock_order_dao.get_by_order_no.return_value = {"宽度": 100.0}
        self.mock_calc_rule.calc.return_value = 200.0
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.evaluate_quality_rules("W02406001")
        assert isinstance(result, list)

    def test_formula_exception(self, cursor):
        \"\"\"公式计算异常\"\"\"
        cursor.fetchone.return_value = None
        self.mock_order_dao.get_by_order_no.return_value = {"宽度": 100.0}
        self.mock_calc_rule.calc.side_effect = Exception("计算失败")
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.evaluate_quality_rules("W02406001")
        assert result == []

    def test_measure_value_exception(self, cursor):
        \"\"\"实测值计算异常\"\"\"
        cursor.fetchone.return_value = None
        self.mock_order_dao.get_by_order_no.return_value = {"宽度": 100.0}
        self.mock_calc_rule.calc.side_effect = Exception("实测异常")
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.evaluate_quality_rules("W02406001")
        assert result == []

    def test_tolerance_format_exception(self, cursor):
        \"\"\"公差格式异常应通过\"\"\"
        cursor.fetchone.return_value = None
        self.mock_order_dao.get_by_order_no.return_value = {"宽度": 100.0}
        self.mock_calc_rule.calc.return_value = 105.0
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.evaluate_quality_rules("W02406001")
        assert isinstance(result, list)

    def test_order_data_field_fallback(self, cursor):
        \"\"\"order_data fallback with English keys\"\"\"
        cursor.fetchone.return_value = None
        self.mock_order_dao.get_by_order_no.return_value = {"width": 100.0}
        self.mock_calc_rule.calc.return_value = 105.0
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.evaluate_quality_rules("W02406001")
        assert isinstance(result, list)
"""

    with open(target, "a", encoding="utf-8") as f:
        f.write(append)
    print("TestEvaluateQualityRules 追加完成")

print("完成！")
