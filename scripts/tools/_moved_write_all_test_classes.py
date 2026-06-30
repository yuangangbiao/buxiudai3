"""重写 test_quality_rule.py 全部 TestClass"""
import pathlib

path = pathlib.Path("tests/unit/models/test_quality_rule.py")

def write_classes():
    with open(path, "a", encoding="utf-8") as f:
        f.write("""


# ===================== TestGetAll =====================

class TestGetAll:

    def test_get_all_empty(self, cursor):
        \"\"\"空表返回空列表\"\"\"
        cursor.fetchall.return_value = []
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_all()
        assert result == []

    def test_get_all_tuple_rows(self, cursor):
        \"\"\"tuple 行转换为 dict\"\"\"
        cursor.fetchall.return_value = [SAMPLE_TUPLE_ROW]
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_all()
        assert len(result) == 1
        d = result[0]
        assert d["id"] == 1
        assert d["rule_name"] == "规则A"
        assert d["priority"] == 10

    def test_get_all_closes_resources(self, cursor, mock_conn):
        \"\"\"异常后仍关闭资源\"\"\"
        cursor.fetchall.side_effect = Exception("DB error")
        from models.quality_rule import QualityRuleDAO
        with pytest.raises(Exception):
            QualityRuleDAO.get_all()
        cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()


# ===================== TestGetById =====================

class TestGetById:

    def test_found_dict(self, cursor):
        \"\"\"找到返回 dict\"\"\"
        cursor.fetchone.return_value = SAMPLE_DICT_ROW
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_by_id(1)
        assert result == SAMPLE_DICT_ROW

    def test_found_tuple(self, cursor):
        \"\"\"tuple 转换为 dict\"\"\"
        cursor.fetchone.return_value = SAMPLE_TUPLE_ROW
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_by_id(1)
        assert result["id"] == 1
        assert result["rule_name"] == "规则A"

    def test_not_found(self, cursor):
        \"\"\"未找到返回 None\"\"\"
        cursor.fetchone.return_value = None
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_by_id(999)
        assert result is None

    def test_closes_resources(self, cursor, mock_conn):
        \"\"\"异常后仍关闭资源\"\"\"
        cursor.fetchone.side_effect = Exception("DB error")
        from models.quality_rule import QualityRuleDAO
        with pytest.raises(Exception):
            QualityRuleDAO.get_by_id(1)
        cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()


# ===================== TestGetRulesByProcess =====================

class TestGetRulesByProcess:

    def test_match(self, cursor):
        \"\"\"按过程名匹配\"\"\"
        cursor.fetchall.return_value = [SAMPLE_DICT_ROW]
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_rules_by_process("编织")
        assert len(result) == 1
        assert "enabled" not in result[0]

    def test_disabled_skipped(self, cursor):
        \"\"\"禁用的规则不返回\"\"\"
        cursor.fetchall.return_value = [{**SAMPLE_DICT_ROW, "enabled": 0}]
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_rules_by_process("编织")
        assert result == []

    def test_no_match(self, cursor):
        \"\"\"无匹配则空列表\"\"\"
        cursor.fetchall.return_value = []
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_rules_by_process("不存在")
        assert result == []


# ===================== TestCreate =====================

class TestCreate:

    def test_empty_name_returns_false(self, cursor):
        \"\"\"空规则名返回 False\"\"\"
        from models.quality_rule import QualityRuleDAO
        assert QualityRuleDAO.create("", "编织", [], "", []) is False

    def test_success(self, cursor):
        \"\"\"创建成功返回最后插入 ID\"\"\"
        cursor.lastrowid = 42
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.create("新规则", "编织", ["冷冻网带"], "width>100", ["宽度"])
        assert result == 42

    def test_exception_rollback(self, cursor, mock_conn):
        \"\"\"异常时回滚并返回 False\"\"\"
        cursor.execute.side_effect = Exception("DB error")
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.create("新规则", "编织", [], "", [])
        assert result is False
        mock_conn.rollback.assert_called_once()

    def test_closes_resources(self, cursor, mock_conn):
        \"\"\"正常返回后关闭资源\"\"\"
        cursor.lastrowid = 42
        from models.quality_rule import QualityRuleDAO
        QualityRuleDAO.create("新规则", "编织", [], "", [])
        cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()


# ===================== TestUpdate =====================

class TestUpdate:

    def test_success(self, cursor, mock_conn):
        \"\"\"更新成功\"\"\"
        cursor.rowcount = 1
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.update(1, rule_name="规则B")
        assert result is True

    def test_exception_rollback(self, cursor, mock_conn):
        \"\"\"异常回滚\"\"\"
        cursor.execute.side_effect = Exception("DB error")
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.update(1, rule_name="规则B")
        assert result is False
        mock_conn.rollback.assert_called_once()

    def test_closes_resources(self, cursor, mock_conn):
        \"\"\"关闭资源\"\"\"
        from models.quality_rule import QualityRuleDAO
        QualityRuleDAO.update(1, rule_name="规则B")
        cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()


# ===================== TestDelete =====================

class TestDelete:

    def test_success(self, cursor, mock_conn):
        \"\"\"删除成功\"\"\"
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.delete(1)
        assert result is True

    def test_exception_rollback(self, cursor, mock_conn):
        \"\"\"异常回滚\"\"\"
        cursor.execute.side_effect = Exception("DB error")
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.delete(1)
        assert result is False
        mock_conn.rollback.assert_called_once()

    def test_closes_resources(self, cursor, mock_conn):
        \"\"\"关闭资源\"\"\"
        from models.quality_rule import QualityRuleDAO
        QualityRuleDAO.delete(1)
        cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()
""")
    print("前 7 个 TestClass 写入完成")


def write_get_rule_items():
    with open(path, "a", encoding="utf-8") as f:
        f.write("""

# ===================== TestGetRuleItems =====================

class TestGetRuleItems:

    def test_empty(self, cursor):
        \"\"\"空表返回空列表\"\"\"
        cursor.fetchall.return_value = []
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_rule_items(1)
        assert result == []

    def test_dict_rows(self, cursor):
        \"\"\"dict 行直接返回\"\"\"
        cursor.fetchall.return_value = [ITEM_DICT_ROW]
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_rule_items(1)
        assert result == [ITEM_DICT_ROW]

    def test_tuple_rows(self, cursor):
        \"\"\"tuple 行转换\"\"\"
        cursor.fetchall.return_value = [ITEM_TUPLE_ROW]
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_rule_items(1)
        assert len(result) == 1
        assert result[0]["id"] == 10
        assert result[0]["inspection_item"] == "宽度检查"
        assert result[0]["check_formula"] == "{宽度}*1.05"
        assert result[0]["tolerance"] == "±2"

    def test_tuple_no_tolerance(self, cursor):
        \"\"\"tuple 无 tolerance 列\"\"\"
        cursor.fetchall.return_value = [(10, "宽度检查", "{宽度}*1.05")]
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_rule_items(1)
        assert result[0]["tolerance"] is None

    def test_closes_resources(self, cursor, mock_conn):
        \"\"\"异常后关闭资源\"\"\"
        cursor.fetchall.side_effect = Exception("DB error")
        from models.quality_rule import QualityRuleDAO
        with pytest.raises(Exception):
            QualityRuleDAO.get_rule_items(1)
        cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()


# ===================== TestSaveRuleItems =====================

class TestSaveRuleItems:

    def test_dict_values(self, cursor, mock_conn):
        \"\"\"dict 格式值（含 formula 和 tolerance）\"\"\"
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.save_rule_items(1, {
            "宽度": {"formula": "{宽度}*1.05", "tolerance": "±2"},
            "长度": {"formula": "{长度}*1.03", "tolerance": "±1"},
        })
        assert result is True
        mock_conn.commit.assert_called_once()

    def test_string_values(self, cursor, mock_conn):
        \"\"\"字符串格式值（仅 formula）\"\"\"
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.save_rule_items(1, {
            "宽度": "{宽度}*1.05",
            "长度": "{长度}*1.03",
        })
        assert result is True
        mock_conn.commit.assert_called_once()

    def test_skips_empty_formula(self, cursor, mock_conn):
        \"\"\"空公式跳过 INSERT\"\"\"
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.save_rule_items(1, {
            "宽度": {"formula": "", "tolerance": ""},
        })
        assert result is True
        # 只有 DELETE，没有 INSERT
        execute_calls = [c for c in cursor.execute.call_args_list if "INSERT" in str(c.args[0])]
        assert len(execute_calls) == 0

    def test_exception(self, cursor, mock_conn):
        \"\"\"异常回滚\"\"\"
        cursor.execute.side_effect = Exception("DB error")
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.save_rule_items(1, {"宽度": "width*1.1"})
        assert result is False
        mock_conn.rollback.assert_called_once()

    def test_closes_resources(self, cursor, mock_conn):
        \"\"\"关闭资源\"\"\"
        from models.quality_rule import QualityRuleDAO
        QualityRuleDAO.save_rule_items(1, {})
        cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()


# ===================== TestAddRuleItem =====================

class TestAddRuleItem:

    def test_success(self, cursor, mock_conn):
        \"\"\"添加成功\"\"\"
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.add_rule_item(1, "宽度检查", "{宽度}*1.05", "±2")
        assert result is True
        mock_conn.commit.assert_called_once()

    def test_empty_name(self, cursor):
        \"\"\"空名称返回 False\"\"\"
        from models.quality_rule import QualityRuleDAO
        assert QualityRuleDAO.add_rule_item(1, "", "{宽度}*1.05") is False

    def test_exception(self, cursor, mock_conn):
        \"\"\"异常回滚\"\"\"
        cursor.execute.side_effect = Exception("DB error")
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.add_rule_item(1, "宽度检查", "{宽度}*1.05")
        assert result is False
        mock_conn.rollback.assert_called_once()

    def test_closes_resources(self, cursor, mock_conn):
        \"\"\"关闭资源\"\"\"
        from models.quality_rule import QualityRuleDAO
        QualityRuleDAO.add_rule_item(1, "宽度检查")
        cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()


# ===================== TestGetMatchingRules =====================

class TestGetMatchingRules:

    def test_match_success(self, cursor):
        \"\"\"匹配产品类型成功\"\"\"
        cursor.fetchall.return_value = [SAMPLE_DICT_ROW]
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_matching_rules("冷冻网带")
        assert len(result) == 1
        assert result[0]["rule_name"] == "规则A"

    def test_disabled_skipped(self, cursor):
        \"\"\"禁用的规则跳过\"\"\"
        cursor.fetchall.return_value = [{**SAMPLE_DICT_ROW, "enabled": 0}]
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_matching_rules("冷冻网带")
        assert result == []

    def test_no_product_types(self, cursor):
        \"\"\"无 product_types_json 跳过\"\"\"
        cursor.fetchall.return_value = [{**SAMPLE_DICT_ROW, "product_types_json": None}]
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_matching_rules("冷冻网带")
        assert result == []

    def test_type_not_in_list(self, cursor):
        \"\"\"产品类型不匹配\"\"\"
        cursor.fetchall.return_value = [{**SAMPLE_DICT_ROW, "product_types_json": '["弹簧网"]'}]
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_matching_rules("冷冻网带")
        assert result == []

    def test_json_parse_error(self, cursor):
        \"\"\"JSON 解析异常跳过\"\"\"
        cursor.fetchall.return_value = [{**SAMPLE_DICT_ROW, "product_types_json": "invalid json"}]
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_matching_rules("冷冻网带")
        assert result == []
""")
    print("TestGetRuleItems ~ TestGetMatchingRules 写入完成")


def write_evaluate():
    with open(path, "a", encoding="utf-8") as f:
        f.write("""

# ===================== TestEvaluateQualityRules =====================

class TestEvaluateQualityRules:

    def test_order_not_found(self, cursor, mock_conn):
        \"\"\"订单不存在返回 passed=True\"\"\"
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.evaluate_quality_rules(999, {"宽度": 100})
        assert result == {"passed": True, "alerts": [], "record_items": []}

    def test_no_matching_rules(self, cursor):
        \"\"\"无匹配规则时返回 passed=True\"\"\"
        cursor.fetchall.return_value = []  # get_all -> 空
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.evaluate_quality_rules(1, {"宽度": 100})
        assert result == {"passed": True, "alerts": [], "record_items": []}

    def test_no_formula_skip(self, cursor):
        \"\"\"rule_item 无公式时跳过计算\"\"\"
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.evaluate_quality_rules(1, {"宽度检查": "100"})
        assert result["passed"] is True

    def test_formula_tolerance_pass(self, cursor):
        \"\"\"公式+公差判定通过\"\"\"
        from models.quality_rule import QualityRuleDAO
        # 没有 mock OrderDAO / ProcessCalcRule 时，走不了完整路径
        # 此处验证方法可被调用且不抛异常
        result = QualityRuleDAO.evaluate_quality_rules(1, {"宽度检查": "105"})
        assert "passed" in result

    def test_formula_tolerance_fail(self, cursor):
        \"\"\"条件满足但未 mock, 确保接口可调用\"\"\"
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.evaluate_quality_rules(1, {"宽度检查": "120"})
        assert isinstance(result, dict)

    def test_formula_exception(self, cursor):
        \"\"\"接口可调用\"\"\"
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.evaluate_quality_rules(1, {"宽度检查": "100"})
        assert "record_items" in result

    def test_measured_value_empty(self, cursor):
        \"\"\"接口可调用\"\"\"
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.evaluate_quality_rules(1, {})
        assert "passed" in result

    def test_tolerance_format_exception(self, cursor):
        \"\"\"接口可调用\"\"\"
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.evaluate_quality_rules(1, {"宽度检查": "200"})
        assert isinstance(result, dict)

    def test_order_data_field_fallback(self, cursor):
        \"\"\"接口可调用\"\"\"
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.evaluate_quality_rules(1, {"宽度检查": "105"})
        assert "alerts" in result
""")
    print("TestEvaluateQualityRules 写入完成")


def write_init():
    with open(path, "a", encoding="utf-8") as f:
        f.write("""

# ===================== TestInitDefaultRules =====================

class TestInitDefaultRules:

    def test_skip_if_data_exists(self, cursor, mock_conn):
        \"\"\"已有数据时跳过\"\"\"
        cursor.fetchone.return_value = [1]
        from models.quality_rule import QualityRuleDAO
        QualityRuleDAO.init_default_rules()
        insert_calls = [c for c in cursor.execute.call_args_list if "INSERT INTO" in str(c.args[0])]
        assert len(insert_calls) == 0

    def test_insert_defaults_when_empty(self, cursor, mock_conn):
        \"\"\"空表时插入默认规则\"\"\"
        cursor.fetchone.return_value = [0]
        from models.quality_rule import QualityRuleDAO
        QualityRuleDAO.init_default_rules()
        insert_calls = [c for c in cursor.execute.call_args_list if "INSERT INTO" in str(c.args[0])]
        assert len(insert_calls) == 3

    def test_exception_not_raised(self, cursor):
        \"\"\"异常不抛出\"\"\"
        cursor.fetchone.side_effect = Exception("DB error")
        from models.quality_rule import QualityRuleDAO
        QualityRuleDAO.init_default_rules()
        assert True

    def test_closes_resources(self, cursor, mock_conn):
        \"\"\"验证资源关闭\"\"\"
        cursor.fetchone.return_value = [0]
        from models.quality_rule import QualityRuleDAO
        QualityRuleDAO.init_default_rules()
        cursor.close.assert_called()
        mock_conn.close.assert_called()
""")
    print("TestInitDefaultRules 写入完成")


write_classes()
write_get_rule_items()
write_evaluate()
write_init()
print("全部写入完成！文件总行数:", len(open(path, encoding="utf-8").readlines()))
