"""追加 TestEvaluateQualityRules 和 TestInitDefaultRules 到测试文件"""
import pathlib

target = pathlib.Path("tests/unit/models/test_quality_rule.py")
content = target.read_text(encoding="utf-8")

# ===== TestEvaluateQualityRules =====
if "class TestEvaluateQualityRules" in content:
    print("TestEvaluateQualityRules 已存在，跳过")
else:
    append = """

class TestEvaluateQualityRules:
    \"\"\"Test QualityRuleDAO.evaluate_quality_rules\"\"\"

    @pytest.fixture(autouse=True)
    def patch_order_dao(self):
        with patch("models.quality_rule.OrderDAO") as mock:
            self.mock_order_dao_obj = mock
            yield mock

    @pytest.fixture(autouse=True)
    def patch_calc_expr(self):
        with patch("models.quality_rule.ProcessCalcRule._calc_expr") as mock:
            yield mock

    @pytest.fixture(autouse=True)
    def patch_get_matching(self):
        with patch.object(QualityRuleDAO, "get_matching_rules") as mock:
            yield mock

    @pytest.fixture(autouse=True)
    def patch_get_rule_items(self):
        with patch.object(QualityRuleDAO, "get_rule_items") as mock:
            yield mock

    def test_order_not_found(self, cursor, patch_get_matching):
        \"\"\"订单不存在返回 passed=True\"\"\"
        self.mock_order_dao_obj.get_by_id.return_value = None
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.evaluate_quality_rules(999, {"宽度": 100})
        assert result == {"passed": True, "alerts": [], "record_items": []}

    def test_no_matching_rules(self, cursor, patch_get_matching):
        \"\"\"无匹配规则时返回 passed=True\"\"\"
        self.mock_order_dao_obj.get_by_id.return_value = {"product_type": "冷冻网带"}
        patch_get_matching.return_value = []
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.evaluate_quality_rules(1, {"宽度": 100})
        assert result == {"passed": True, "alerts": [], "record_items": []}

    def test_no_formula_skip(self, cursor, patch_get_matching, patch_get_rule_items, patch_calc_expr):
        \"\"\"rule_item 无公式时跳过计算，is_passed=True\"\"\"
        self.mock_order_dao_obj.get_by_id.return_value = {"product_type": "冷冻网带", "width": 100}
        patch_get_matching.return_value = [{"id": 1, "rule_name": "测试规则"}]
        patch_get_rule_items.return_value = [
            {"id": 1, "inspection_item": "宽度检查", "check_formula": "", "tolerance": ""}
        ]
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.evaluate_quality_rules(1, {"宽度检查": "100"})
        assert result["passed"] is True
        assert len(result["record_items"]) == 1
        assert result["record_items"][0]["inspection_item"] == "宽度检查"
        assert result["record_items"][0]["is_passed"] is True

    def test_formula_tolerance_pass(self, cursor, patch_get_matching, patch_get_rule_items, patch_calc_expr):
        \"\"\"公式+公差判定通过\"\"\"
        self.mock_order_dao_obj.get_by_id.return_value = {"product_type": "冷冻网带", "宽度": 100}
        patch_get_matching.return_value = [{"id": 1, "rule_name": "测试规则"}]
        patch_get_rule_items.return_value = [
            {"id": 1, "inspection_item": "宽度检查", "check_formula": "{宽度}*1.05", "tolerance": "\\u00b15"}
        ]
        patch_calc_expr.return_value = 105.0
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.evaluate_quality_rules(1, {"宽度检查": "104"})
        assert result["passed"] is True
        assert len(result["alerts"]) == 0

    def test_formula_tolerance_fail(self, cursor, patch_get_matching, patch_get_rule_items, patch_calc_expr):
        \"\"\"公式+公差判定失败，产生警报\"\"\"
        self.mock_order_dao_obj.get_by_id.return_value = {"product_type": "冷冻网带", "宽度": 100}
        patch_get_matching.return_value = [{"id": 1, "rule_name": "测试规则"}]
        patch_get_rule_items.return_value = [
            {"id": 1, "inspection_item": "宽度检查", "check_formula": "{宽度}*1.05", "tolerance": "\\u00b15"}
        ]
        patch_calc_expr.return_value = 105.0
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.evaluate_quality_rules(1, {"宽度检查": "120"})
        assert result["passed"] is False
        assert len(result["alerts"]) == 1

    def test_formula_exception(self, cursor, patch_get_matching, patch_get_rule_items, patch_calc_expr):
        \"\"\"公式计算异常时 standard_value=0\"\"\"
        self.mock_order_dao_obj.get_by_id.return_value = {"product_type": "冷冻网带", "宽度": 100}
        patch_get_matching.return_value = [{"id": 1, "rule_name": "测试规则"}]
        patch_get_rule_items.return_value = [
            {"id": 1, "inspection_item": "宽度检查", "check_formula": "{宽度}*1.05", "tolerance": ""}
        ]
        patch_calc_expr.side_effect = Exception("计算失败")
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.evaluate_quality_rules(1, {"宽度检查": "100"})
        # 公式异常时不触发公差判定（standard_value=0）
        assert result["passed"] is True

    def test_measured_value_invalid(self, cursor, patch_get_matching, patch_get_rule_items, patch_calc_expr):
        \"\"\"实测值为空时 measured=0\"\"\"
        self.mock_order_dao_obj.get_by_id.return_value = {"product_type": "冷冻网带", "宽度": 100}
        patch_get_matching.return_value = [{"id": 1, "rule_name": "测试规则"}]
        patch_get_rule_items.return_value = [
            {"id": 1, "inspection_item": "宽度检查", "check_formula": "{宽度}*1.05", "tolerance": ""}
        ]
        patch_calc_expr.return_value = 105.0
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.evaluate_quality_rules(1, {})
        # 无公差时不触发失败
        assert result["passed"] is True

    def test_tolerance_format_exception(self, cursor, patch_get_matching, patch_get_rule_items, patch_calc_expr):
        \"\"\"公差格式异常时 is_passed=True\"\"\"
        self.mock_order_dao_obj.get_by_id.return_value = {"product_type": "冷冻网带", "宽度": 100}
        patch_get_matching.return_value = [{"id": 1, "rule_name": "测试规则"}]
        patch_get_rule_items.return_value = [
            {"id": 1, "inspection_item": "宽度检查", "check_formula": "{宽度}*1.05", "tolerance": "abc"}
        ]
        patch_calc_expr.return_value = 105.0
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.evaluate_quality_rules(1, {"宽度检查": "200"})
        # tolerance="abc" float解析异常，is_passed=True
        assert result["passed"] is True

    def test_order_data_field_fallback(self, cursor, patch_get_matching, patch_get_rule_items, patch_calc_expr):
        \"\"\"order_data 字段回退（英文key）\"\"\"
        self.mock_order_dao_obj.get_by_id.return_value = {"product_type": "冷冻网带", "width": 100}
        patch_get_matching.return_value = [{"id": 1, "rule_name": "测试规则"}]
        patch_get_rule_items.return_value = [
            {"id": 1, "inspection_item": "宽度检查", "check_formula": "{宽度}*1.05", "tolerance": ""}
        ]
        patch_calc_expr.return_value = 105.0
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.evaluate_quality_rules(1, {"宽度检查": "105"})
        assert result["passed"] is True"""

    with open(target, "a", encoding="utf-8") as f:
        f.write(append)
    print("TestEvaluateQualityRules 追加完成")

# ===== TestInitDefaultRules =====
if "class TestInitDefaultRules" in content:
    print("TestInitDefaultRules 已存在，跳过")
else:
    append2 = """

class TestInitDefaultRules:
    \"\"\"Test QualityRuleDAO.init_default_rules\"\"\"

    def test_skip_if_data_exists(self, cursor):
        \"\"\"已有数据时跳过\"\"\"
        cursor.fetchone.return_value = [1]
        from models.quality_rule import QualityRuleDAO
        QualityRuleDAO.init_default_rules()
        insert_calls = [c for c in cursor.execute.call_args_list if "INSERT INTO" in str(c)]
        assert len(insert_calls) == 0

    def test_insert_defaults_when_empty(self, cursor):
        \"\"\"空表时插入默认规则\"\"\"
        cursor.fetchone.return_value = [0]
        from models.quality_rule import QualityRuleDAO
        QualityRuleDAO.init_default_rules()
        insert_calls = [c for c in cursor.execute.call_args_list if "INSERT INTO" in str(c)]
        assert len(insert_calls) == 3  # 3条默认规则

    def test_exception_not_raised(self, cursor):
        \"\"\"异常不抛出\"\"\"
        cursor.fetchone.side_effect = Exception("数据库异常")
        from models.quality_rule import QualityRuleDAO
        QualityRuleDAO.init_default_rules()
        assert True

    def test_close_resources(self, cursor, mock_conn):
        \"\"\"验证资源关闭\"\"\"
        cursor.fetchone.return_value = [0]
        from models.quality_rule import QualityRuleDAO
        QualityRuleDAO.init_default_rules()
        cursor.close.assert_called()
        mock_conn.close.assert_called()"""

    with open(target, "a", encoding="utf-8") as f:
        f.write(append2)
    print("TestInitDefaultRules 追加完成")

print("所有追加完成")
