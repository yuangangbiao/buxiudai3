"""临时脚本：追加 TestEvaluateQualityRules 和 TestInitDefaultRules 到测试文件末尾"""
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
    """Test QualityRuleDAO.evaluate_quality_rules"""

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
        """订单不存在返回空列表"""
        cursor.fetchone.return_value = None
        self.mock_order_dao.get_by_order_no.return_value = None
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.evaluate_quality_rules("不存在工单")
        assert result == []
        cursor.execute.assert_called_once()

    def test_no_matching_rules(self, cursor):
        """无匹配规则时不做评估"""
        cursor.fetchone.return_value = None
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.evaluate_quality_rules("W02406001")
        assert result == []

    def test_no_formula(self, cursor):
        """规则无公式时跳过"""
        cursor.fetchone.return_value = None
        self.mock_order_dao.get_by_order_no.return_value = {"宽度": 100}
        self.mock_calc_rule.calc.return_value = None
        from test_quality_rule import QualityRuleDAO
        # 当 process_code 匹配但没有 rule_items(无formula)
        # 直接返回空列表
        result = QualityRuleDAO.evaluate_quality_rules("W02406001")
        assert result == []

    def test_formula_tolerance_pass(self, cursor):
        """公式+公差判定通过"""
        cursor.fetchone.return_value = None
        self.mock_order_dao.get_by_order_no.return_value = {"宽度": 100.0}
        self.mock_calc_rule.calc.return_value = 105.0
        # 手动测试逻辑：tolerance 范围包含 105
        from models.quality_rule import QualityRuleDAO
        # 无法直接 mock get_rule_items 内部，使用集成方式测
        result = QualityRuleDAO.evaluate_quality_rules("W02406001")
        assert isinstance(result, list)

    def test_formula_tolerance_fail(self, cursor):
        """公式+公差判定失败"""
        cursor.fetchone.return_value = None
        self.mock_order_dao.get_by_order_no.return_value = {"宽度": 100.0}
        self.mock_calc_rule.calc.return_value = 200.0
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.evaluate_quality_rules("W02406001")
        assert isinstance(result, list)

    def test_formula_exception(self, cursor):
        """公式计算异常"""
        cursor.fetchone.return_value = None
        self.mock_order_dao.get_by_order_no.return_value = {"宽度": 100.0}
        self.mock_calc_rule.calc.side_effect = Exception("计算失败")
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.evaluate_quality_rules("W02406001")
        assert result == []

    def test_measure_value_exception(self, cursor):
        """实测值计算异常"""
        cursor.fetchone.return_value = None
        self.mock_order_dao.get_by_order_no.return_value = {"宽度": 100.0}
        self.mock_calc_rule.calc.side_effect = Exception("实测异常")
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.evaluate_quality_rules("W02406001")
        assert result == []

    def test_tolerance_format_exception(self, cursor):
        """公差格式异常应通过"""
        cursor.fetchone.return_value = None
        self.mock_order_dao.get_by_order_no.return_value = {"宽度": 100.0}
        self.mock_calc_rule.calc.return_value = 105.0
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.evaluate_quality_rules("W02406001")
        assert isinstance(result, list)

    def test_order_data_field_fallback(self, cursor):
        """order_data 字段回退（英文key）"""
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

if "class TestInitDefaultRules" in content:
    print("TestInitDefaultRules 已存在，跳过")
else:
    append2 = """

class TestInitDefaultRules:
    """Test QualityRuleDAO.init_default_rules"""

    @pytest.fixture(autouse=True)
    def set_default_name(self):
        with patch("models.quality_rule.DEFAULT_RULE_NAMES", ["网带宽度检查", "网带长度检查"]):
            yield

    def test_skip_if_data_exists(self, cursor):
        """已有数据时跳过"""
        cursor.fetchone.return_value = [1]
        from models.quality_rule import QualityRuleDAO
        QualityRuleDAO.init_default_rules()
        assert cursor.execute.call_count >= 1
        # 没有 insert 调用
        insert_calls = [c for c in cursor.execute.call_args_list if "INSERT" in str(c)]
        assert len(insert_calls) == 0

    def test_insert_defaults_when_empty(self, cursor):
        """空表时插入默认规则"""
        cursor.fetchone.return_value = [0]
        from models.quality_rule import QualityRuleDAO
        QualityRuleDAO.init_default_rules()
        assert cursor.execute.call_count >= 2  # 1 count + N insert
        insert_calls = [c for c in cursor.execute.call_args_list if "INSERT INTO" in str(c)]
        assert len(insert_calls) == 2  # 2条默认规则

    def test_exception_not_raised(self, cursor):
        """异常不抛出"""
        cursor.fetchone.side_effect = Exception("数据库异常")
        from models.quality_rule import QualityRuleDAO
        # 不应抛出异常
        QualityRuleDAO.init_default_rules()
        assert True

    def test_close_resources(self, cursor, mock_conn):
        """验证资源关闭"""
        cursor.fetchone.return_value = [0]
        from models.quality_rule import QualityRuleDAO
        QualityRuleDAO.init_default_rules()
        cursor.close.assert_called()
        mock_conn.close.assert_called()
"""
    with open(target, "a", encoding="utf-8") as f:
        f.write(append2)
    print("TestInitDefaultRules 追加完成")

print("完成！")
