# -*- coding: utf-8 -*-
"""测试 quality_rule.py — QualityRuleDAO 全覆盖"""
import json
from unittest.mock import patch, MagicMock, PropertyMock

import pytest


# ===================== Fixtures =====================

@pytest.fixture(autouse=True)
def mock_conn():
    """每个测试自动 mock models.quality_rule.get_connection"""
    with patch('models.quality_rule.get_connection') as m:
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchone.return_value = None
        cursor.fetchall.return_value = []
        cursor.rowcount = 1
        m.return_value = conn
        yield conn


@pytest.fixture
def cursor(mock_conn):
    """快捷获取 cursor"""
    return mock_conn.cursor.return_value


# ===================== 测试数据 =====================

SAMPLE_DICT_ROW = {
    "id": 1, "rule_name": "规则A", "process_name": "编织",
    "product_types_json": '["冷冻网带"]', "condition_expr": "width>100",
    "inspection_items_json": '[{"name":"宽度"}]',
    "check_formula": "width*1.1", "priority": 10,
    "enabled": 1, "created_at": "2025-01-01", "updated_at": "2025-06-01"
}

SAMPLE_TUPLE_ROW = (
    1, "规则A", "编织", '["冷冻网带"]', "width>100",
    '[{"name":"宽度"}]', "width*1.1", 10, 1,
    "2025-01-01", "2025-06-01"
)

SAMPLE_DICT_ROW_ENABLED = {
    "id": 1, "rule_name": "规则A", "process_name": "编织",
    "product_types_json": '["冷冻网带"]', "condition_expr": "width>100",
    "inspection_items_json": '[{"name":"宽度"}]',
    "check_formula": "width*1.1", "priority": 10,
    "enabled": 1, "created_at": "2025-01-01", "updated_at": "2025-06-01"
}

SAMPLE_DICT_ROW_DISABLED = {
    "id": 2, "rule_name": "规则B", "process_name": "编织",
    "product_types_json": '["冷冻网带"]', "condition_expr": "",
    "inspection_items_json": '[]',
    "check_formula": "", "priority": 5,
    "enabled": 0, "created_at": "2025-01-01", "updated_at": "2025-06-01"
}

ITEM_DICT_ROW = {
    "id": 10, "inspection_item": "宽度检查",
    "check_formula": "{宽度}*1.05", "tolerance": "±2"
}

ITEM_TUPLE_ROW = (10, "宽度检查", "{宽度}*1.05", "±2")


# ===================== TestGetAll =====================

class TestGetAll:

    def test_get_all_empty(self, cursor):
        """空表返回空列表"""
        cursor.fetchall.return_value = []
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_all()
        assert result == []

    def test_get_all_dict_rows(self, cursor):
        """dict 行直接返回"""
        cursor.fetchall.return_value = [SAMPLE_DICT_ROW]
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_all()
        assert len(result) == 1
        assert result[0] is SAMPLE_DICT_ROW

    def test_get_all_tuple_rows(self, cursor):
        """tuple 行转换为 dict（含 enabled bool 转换）"""
        cursor.fetchall.return_value = [SAMPLE_TUPLE_ROW]
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_all()
        assert len(result) == 1
        d = result[0]
        assert d["id"] == 1
        assert d["rule_name"] == "规则A"
        assert d["priority"] == 10
        assert d["enabled"] is True  # bool(row[8]) → True

    def test_tuple_enabled_is_bool(self, cursor):
        """tuple 中 enabled 字段转为 bool"""
        cursor.fetchall.return_value = [(1, "r", "p", "[]", "", "[]", "", 5, 0, "t1", "t2")]
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_all()
        assert result[0]["enabled"] is False

    def test_get_all_closes_resources(self, cursor, mock_conn):
        """异常后仍关闭资源"""
        cursor.fetchall.side_effect = Exception("DB error")
        from models.quality_rule import QualityRuleDAO
        with pytest.raises(Exception):
            QualityRuleDAO.get_all()
        cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()


# ===================== TestGetById =====================

class TestGetById:

    def test_found_dict(self, cursor):
        """找到返回 dict"""
        cursor.fetchone.return_value = SAMPLE_DICT_ROW
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_by_id(1)
        assert result is SAMPLE_DICT_ROW

    def test_found_tuple(self, cursor):
        """tuple 转换为 dict"""
        cursor.fetchone.return_value = SAMPLE_TUPLE_ROW
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_by_id(1)
        assert result["id"] == 1
        assert result["rule_name"] == "规则A"
        assert result["enabled"] is True

    def test_not_found(self, cursor):
        """未找到返回 None"""
        cursor.fetchone.return_value = None
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_by_id(999)
        assert result is None

    def test_closes_resources(self, cursor, mock_conn):
        """异常后仍关闭资源"""
        cursor.fetchone.side_effect = Exception("DB error")
        from models.quality_rule import QualityRuleDAO
        with pytest.raises(Exception):
            QualityRuleDAO.get_by_id(1)
        cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()


# ===================== TestGetRulesByProcess =====================

class TestGetRulesByProcess:

    def test_match(self, cursor):
        """按过程名匹配 — dict 行含 enabled 字段"""
        cursor.fetchall.return_value = [SAMPLE_DICT_ROW_ENABLED]
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_rules_by_process("编织")
        assert len(result) == 1
        assert result[0]["rule_name"] == "规则A"

    def test_disabled_skipped(self, cursor):
        """禁用的规则不返回"""
        cursor.fetchall.return_value = [SAMPLE_DICT_ROW_DISABLED]
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_rules_by_process("编织")
        assert result == []

    def test_no_match(self, cursor):
        """无匹配返回空列表"""
        cursor.fetchall.return_value = []
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_rules_by_process("不存在")
        assert result == []

    def test_process_name_not_match(self, cursor):
        """process_name 不匹配"""
        cursor.fetchall.return_value = [{**SAMPLE_DICT_ROW, "enabled": 1}]
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_rules_by_process("焊接")
        assert result == []

    def test_enabled_default_true(self, cursor):
        """enabled 字段缺失时视为启用"""
        row_no_enabled = {k: v for k, v in SAMPLE_DICT_ROW.items() if k != "enabled"}
        cursor.fetchall.return_value = [row_no_enabled]
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_rules_by_process("编织")
        # dict 行不会进入 tuple 分支，所以 enabled 会保持原样
        # 但 source code 对 tuple 行做 bool()，对 dict 行直接返回
        # 这里 enabled 字段不存在，get("enabled", True) → True
        assert len(result) == 1

    def test_tuple_disabled(self, cursor):
        """tuple 行 enabled=False 跳过"""
        disabled_tuple = (1, "r", "编织", "[]", "", "[]", "", 5, 0, "t1", "t2")
        cursor.fetchall.return_value = [disabled_tuple]
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_rules_by_process("编织")
        assert result == []


# ===================== TestCreate =====================

class TestCreate:

    def test_empty_name_returns_false(self, cursor):
        """空规则名返回 (False, msg, None)"""
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.create("", "编织", [], "", [])
        assert result[0] is False
        assert "不能为空" in result[1]
        assert result[2] is None

    def test_success(self, cursor):
        """创建成功返回 (True, msg, id)"""
        cursor.lastrowid = 42
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.create("新规则", "编织", ["冷冻网带"], "width>100", ["宽度"])
        assert result[0] is True
        assert result[2] == 42

    def test_exception_rollback(self, cursor, mock_conn):
        """异常时回滚并返回 (False, msg, None)"""
        cursor.execute.side_effect = Exception("DB error")
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.create("新规则", "编织", [], "", [])
        assert result[0] is False
        assert "DB error" in result[1]
        assert result[2] is None
        mock_conn.rollback.assert_called_once()

    def test_closes_resources(self, cursor, mock_conn):
        """正常返回后关闭资源"""
        cursor.lastrowid = 42
        from models.quality_rule import QualityRuleDAO
        QualityRuleDAO.create("新规则", "编织", [], "", [])
        cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()


# ===================== TestUpdate =====================

class TestUpdate:

    def test_success(self, cursor, mock_conn):
        """更新成功返回 (True, msg, id)"""
        cursor.rowcount = 1
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.update(
            1, "规则B", ["冷冻网带"], "", [],
            check_formula="", priority=5, enabled=True, process_name="编织"
        )
        assert result[0] is True
        assert result[2] == 1

    def test_exception_rollback(self, cursor, mock_conn):
        """异常回滚返回 (False, msg, None)"""
        cursor.execute.side_effect = Exception("DB error")
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.update(
            1, "规则B", ["冷冻网带"], "", [],
            check_formula="", priority=5, enabled=True, process_name="编织"
        )
        assert result[0] is False
        assert "DB error" in result[1]
        mock_conn.rollback.assert_called_once()

    def test_closes_resources(self, cursor, mock_conn):
        """关闭资源"""
        from models.quality_rule import QualityRuleDAO
        QualityRuleDAO.update(
            1, "规则B", ["冷冻网带"], "", [],
            check_formula="", priority=5, enabled=True, process_name="编织"
        )
        cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()


# ===================== TestDelete =====================

class TestDelete:

    def test_success(self, cursor, mock_conn):
        """删除成功返回 (True, msg)"""
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.delete(1)
        assert result[0] is True
        assert "删除成功" in result[1]

    def test_exception_rollback(self, cursor, mock_conn):
        """异常回滚返回 (False, msg)"""
        cursor.execute.side_effect = Exception("DB error")
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.delete(1)
        assert result[0] is False
        assert "DB error" in result[1]
        mock_conn.rollback.assert_called_once()

    def test_closes_resources(self, cursor, mock_conn):
        """关闭资源"""
        from models.quality_rule import QualityRuleDAO
        QualityRuleDAO.delete(1)
        cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    def test_rowcount_zero(self, cursor, mock_conn):
        """影响行数为0也返回成功（无异常即为成功）"""
        cursor.rowcount = 0
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.delete(999)
        assert result[0] is True


# ===================== TestGetRuleItems =====================

class TestGetRuleItems:

    def test_empty(self, cursor):
        """空表返回空列表"""
        cursor.fetchall.return_value = []
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_rule_items(1)
        assert result == []

    def test_dict_rows(self, cursor):
        """dict 行直接返回"""
        cursor.fetchall.return_value = [ITEM_DICT_ROW]
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_rule_items(1)
        assert result == [ITEM_DICT_ROW]

    def test_tuple_rows(self, cursor):
        """tuple 行转换"""
        cursor.fetchall.return_value = [ITEM_TUPLE_ROW]
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_rule_items(1)
        assert len(result) == 1
        assert result[0]["id"] == 10
        assert result[0]["inspection_item"] == "宽度检查"
        assert result[0]["check_formula"] == "{宽度}*1.05"
        assert result[0]["tolerance"] == "±2"

    def test_tuple_no_tolerance(self, cursor):
        """tuple 无 tolerance 列"""
        cursor.fetchall.return_value = [(10, "宽度检查", "{宽度}*1.05")]
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_rule_items(1)
        assert result[0]["tolerance"] is None

    def test_closes_resources(self, cursor, mock_conn):
        """异常后关闭资源"""
        cursor.fetchall.side_effect = Exception("DB error")
        from models.quality_rule import QualityRuleDAO
        with pytest.raises(Exception):
            QualityRuleDAO.get_rule_items(1)
        cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()


# ===================== TestSaveRuleItems =====================

class TestSaveRuleItems:

    def test_dict_values(self, cursor, mock_conn):
        """dict 格式值（含 formula 和 tolerance）"""
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.save_rule_items(1, {
            "宽度": {"formula": "{宽度}*1.05", "tolerance": "±2"},
            "长度": {"formula": "{长度}*1.03", "tolerance": "±1"},
        })
        assert result is True
        mock_conn.commit.assert_called_once()

    def test_string_values(self, cursor, mock_conn):
        """字符串格式值（仅 formula）"""
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.save_rule_items(1, {
            "宽度": "{宽度}*1.05",
            "长度": "{长度}*1.03",
        })
        assert result is True
        mock_conn.commit.assert_called_once()

    def test_skips_empty_formula(self, cursor, mock_conn):
        """空公式跳过 INSERT"""
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.save_rule_items(1, {
            "宽度": {"formula": "", "tolerance": ""},
        })
        assert result is True
        # 只有 DELETE，没有 INSERT
        execute_calls = [c for c in cursor.execute.call_args_list if "INSERT" in str(c.args[0])]
        assert len(execute_calls) == 0

    def test_exception(self, cursor, mock_conn):
        """异常回滚"""
        cursor.execute.side_effect = Exception("DB error")
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.save_rule_items(1, {"宽度": "width*1.1"})
        assert result is False
        mock_conn.rollback.assert_called_once()

    def test_whitespace_formula_skipped(self, cursor, mock_conn):
        """只有空格的公式也跳过"""
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.save_rule_items(1, {
            "宽度": {"formula": "   ", "tolerance": ""},
        })
        assert result is True

    def test_closes_resources(self, cursor, mock_conn):
        """关闭资源"""
        from models.quality_rule import QualityRuleDAO
        QualityRuleDAO.save_rule_items(1, {})
        cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()


# ===================== TestAddRuleItem =====================

class TestAddRuleItem:

    def test_success(self, cursor, mock_conn):
        """添加成功"""
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.add_rule_item(1, "宽度检查", "{宽度}*1.05", "±2")
        assert result is True
        mock_conn.commit.assert_called_once()

    def test_empty_name(self, cursor):
        """空名称返回 False"""
        from models.quality_rule import QualityRuleDAO
        assert QualityRuleDAO.add_rule_item(1, "", "{宽度}*1.05") is False

    def test_exception(self, cursor, mock_conn):
        """异常回滚"""
        cursor.execute.side_effect = Exception("DB error")
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.add_rule_item(1, "宽度检查", "{宽度}*1.05")
        assert result is False
        mock_conn.rollback.assert_called_once()

    def test_none_formula_defaults_empty(self, cursor, mock_conn):
        """None 公式转为空字符串"""
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.add_rule_item(1, "宽度检查", None, None)
        assert result is True

    def test_closes_resources(self, cursor, mock_conn):
        """关闭资源"""
        from models.quality_rule import QualityRuleDAO
        QualityRuleDAO.add_rule_item(1, "宽度检查")
        cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()


# ===================== TestGetMatchingRules =====================

class TestGetMatchingRules:

    def test_match_success(self, cursor):
        """匹配产品类型成功"""
        cursor.fetchall.return_value = [{**SAMPLE_DICT_ROW, "enabled": 1}]
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_matching_rules("冷冻网带")
        assert len(result) == 1
        assert result[0]["rule_name"] == "规则A"

    def test_disabled_skipped(self, cursor):
        """禁用的规则跳过"""
        cursor.fetchall.return_value = [{**SAMPLE_DICT_ROW, "enabled": 0}]
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_matching_rules("冷冻网带")
        assert result == []

    def test_no_product_types(self, cursor):
        """无 product_types_json 跳过"""
        cursor.fetchall.return_value = [{**SAMPLE_DICT_ROW, "product_types_json": None}]
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_matching_rules("冷冻网带")
        assert result == []

    def test_type_not_in_list(self, cursor):
        """产品类型不匹配"""
        cursor.fetchall.return_value = [{**SAMPLE_DICT_ROW, "product_types_json": '["弹簧网"]'}]
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_matching_rules("冷冻网带")
        assert result == []

    def test_json_parse_error(self, cursor):
        """JSON 解析异常跳过"""
        cursor.fetchall.return_value = [{**SAMPLE_DICT_ROW, "product_types_json": "invalid json"}]
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_matching_rules("冷冻网带")
        assert result == []

    def test_product_types_already_list(self, cursor):
        """product_types_json 已经是 list"""
        cursor.fetchall.return_value = [{**SAMPLE_DICT_ROW, "product_types_json": ["冷冻网带"]}]
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.get_matching_rules("冷冻网带")
        assert len(result) == 1


# ===================== TestEvaluateQualityRules =====================

class TestEvaluateQualityRules:

    def _setup_mocks(self, cursor, mock_conn, mock_order=None,
                     mock_rules=None, mock_items=None, mock_calc_result=100.0):
        """
        统一设置 evaluate_quality_rules 所需的 mock：
        - OrderDAO.get_by_id
        - QualityRuleDAO.get_all (via get_matching_rules)
        - QualityRuleDAO.get_rule_items
        - ProcessCalcEngine._calc_expr
        """
        if mock_order is None:
            mock_order = {"product_type": "冷冻网带", "width": 100, "长度": 200}
        if mock_rules is None:
            mock_rules = [{**SAMPLE_DICT_ROW, "id": 5, "enabled": 1}]
        if mock_items is None:
            mock_items = [{
                "id": 1, "inspection_item": "宽度检查",
                "check_formula": "{宽度}*1.1", "tolerance": "±5"
            }]

        # mock OrderDAO.get_by_id → 返回订单
        patcher_order = patch('models.order.OrderDAO')
        mock_order_dao = patcher_order.start()
        mock_order_dao.get_by_id.return_value = mock_order

        # mock get_all → 给 get_matching_rules 用
        cursor.fetchall.return_value = mock_rules

        # mock get_rule_items
        patcher_items = patch.object(
            QualityRuleDAO_from_import(), 'get_rule_items',
            return_value=mock_items
        )
        mock_get_items = patcher_items.start()

        # mock ProcessCalcRule._calc_expr
        patcher_calc = patch('models.process_calc_rule.ProcessCalcEngine._calc_expr',
                             return_value=mock_calc_result)
        mock_calc = patcher_calc.start()

        def cleanup():
            patcher_order.stop()
            # patcher_items is patch.object, need to stop
            patcher_items.stop()
            patcher_calc.stop()

        return cleanup

    def _mock_get_matching_rules(self, rules):
        """mock get_matching_rules 直接返回指定列表"""
        patcher = patch.object(QualityRuleDAO_from_import(), 'get_matching_rules',
                               return_value=rules)
        m = patcher.start()
        return (patcher, m)

    def test_order_not_found(self, cursor, mock_conn):
        """订单不存在返回 passed=True"""
        patcher = patch('models.order.OrderDAO')
        mock_order_dao = patcher.start()
        mock_order_dao.get_by_id.return_value = None
        try:
            from models.quality_rule import QualityRuleDAO
            result = QualityRuleDAO.evaluate_quality_rules(999, {"宽度": 100})
            assert result == {"passed": True, "alerts": [], "record_items": []}
        finally:
            patcher.stop()

    def test_no_matching_rules(self, cursor, mock_conn):
        """无匹配规则时返回 passed=True"""
        patcher = patch('models.quality_rule.QualityRuleDAO.get_matching_rules',
                        return_value=[])
        patcher.start()
        patcher_order = patch('models.order.OrderDAO')
        mo = patcher_order.start()
        mo.get_by_id.return_value = {"product_type": "冷冻网带"}
        try:
            from models.quality_rule import QualityRuleDAO
            result = QualityRuleDAO.evaluate_quality_rules(1, {"宽度": 100})
            assert result == {"passed": True, "alerts": [], "record_items": []}
        finally:
            patcher.stop()
            patcher_order.stop()

    def test_no_formula_skip(self, cursor, mock_conn):
        """rule_item 无公式时跳过计算，is_passed=True"""
        patcher_order = patch('models.order.OrderDAO')
        mo = patcher_order.start()
        mo.get_by_id.return_value = {"product_type": "冷冻网带", "width": 100}
        patcher_mr = patch('models.quality_rule.QualityRuleDAO.get_matching_rules',
                           return_value=[{**SAMPLE_DICT_ROW, "id": 5, "enabled": 1}])
        patcher_mr.start()
        patcher_items = patch('models.quality_rule.QualityRuleDAO.get_rule_items',
                              return_value=[{
                                  "id": 1, "inspection_item": "宽度检查",
                                  "check_formula": "", "tolerance": ""
                              }])
        patcher_items.start()
        try:
            from models.quality_rule import QualityRuleDAO
            result = QualityRuleDAO.evaluate_quality_rules(1, {"宽度检查": "100"})
            assert result["passed"] is True
            # 无公式 → 无 record_items 中的 formula 过滤
        finally:
            patcher_order.stop()
            patcher_mr.stop()
            patcher_items.stop()

    def test_formula_tolerance_pass(self, cursor, mock_conn):
        """公式+公差判定通过"""
        patcher_order = patch('models.order.OrderDAO')
        mo = patcher_order.start()
        mo.get_by_id.return_value = {"product_type": "冷冻网带", "width": 100}
        patcher_mr = patch('models.quality_rule.QualityRuleDAO.get_matching_rules',
                           return_value=[{**SAMPLE_DICT_ROW, "id": 5, "enabled": 1}])
        patcher_mr.start()
        patcher_items = patch('models.quality_rule.QualityRuleDAO.get_rule_items',
                              return_value=[{
                                  "id": 1, "inspection_item": "宽度检查",
                                  "check_formula": "{宽度}*1.1", "tolerance": "±5"
                              }])
        patcher_items.start()
        patcher_calc = patch('models.process_calc_rule.ProcessCalcEngine._calc_expr',
                             return_value=105.0)
        patcher_calc.start()
        try:
            from models.quality_rule import QualityRuleDAO
            # 测量值105，标准值105，公差±5 → is_passed=True
            result = QualityRuleDAO.evaluate_quality_rules(1, {"宽度检查": "105"})
            assert result["passed"] is True
            assert len(result["record_items"]) == 1
            assert result["record_items"][0]["is_passed"] is True
        finally:
            patcher_order.stop()
            patcher_mr.stop()
            patcher_items.stop()
            patcher_calc.stop()

    def test_formula_tolerance_fail(self, cursor, mock_conn):
        """测量值超出公差范围"""
        patcher_order = patch('models.order.OrderDAO')
        mo = patcher_order.start()
        mo.get_by_id.return_value = {"product_type": "冷冻网带", "width": 100}
        patcher_mr = patch('models.quality_rule.QualityRuleDAO.get_matching_rules',
                           return_value=[{**SAMPLE_DICT_ROW, "id": 5, "enabled": 1}])
        patcher_mr.start()
        patcher_items = patch('models.quality_rule.QualityRuleDAO.get_rule_items',
                              return_value=[{
                                  "id": 1, "inspection_item": "宽度检查",
                                  "check_formula": "{宽度}*1.1", "tolerance": "±5"
                              }])
        patcher_items.start()
        patcher_calc = patch('models.process_calc_rule.ProcessCalcEngine._calc_expr',
                             return_value=105.0)
        patcher_calc.start()
        try:
            from models.quality_rule import QualityRuleDAO
            # 测量值120，标准值105，公差±5 → 超出
            result = QualityRuleDAO.evaluate_quality_rules(1, {"宽度检查": "120"})
            assert result["passed"] is False
            assert len(result["alerts"]) == 1
        finally:
            patcher_order.stop()
            patcher_mr.stop()
            patcher_items.stop()
            patcher_calc.stop()

    def test_formula_exception(self, cursor, mock_conn):
        """计算公式异常时 standard_value=0 不触发公差失败"""
        patcher_order = patch('models.order.OrderDAO')
        mo = patcher_order.start()
        mo.get_by_id.return_value = {"product_type": "冷冻网带"}
        patcher_mr = patch('models.quality_rule.QualityRuleDAO.get_matching_rules',
                           return_value=[{**SAMPLE_DICT_ROW, "id": 5, "enabled": 1}])
        patcher_mr.start()
        patcher_items = patch('models.quality_rule.QualityRuleDAO.get_rule_items',
                              return_value=[{
                                  "id": 1, "inspection_item": "宽度检查",
                                  "check_formula": "{宽度}*1.1", "tolerance": "±5"
                              }])
        patcher_items.start()
        patcher_calc = patch('models.process_calc_rule.ProcessCalcEngine._calc_expr',
                             side_effect=Exception("calc error"))
        patcher_calc.start()
        try:
            from models.quality_rule import QualityRuleDAO
            result = QualityRuleDAO.evaluate_quality_rules(1, {"宽度检查": "100"})
            assert "record_items" in result
            # standard_value = 0, tolerance ±5, 标准值0 → 不触发公差判断
            assert result["record_items"][0]["standard_value"] == "0"
        finally:
            patcher_order.stop()
            patcher_mr.stop()
            patcher_items.stop()
            patcher_calc.stop()

    def test_measured_value_empty(self, cursor, mock_conn):
        """实测值为空时 measured=0"""
        patcher_order = patch('models.order.OrderDAO')
        mo = patcher_order.start()
        mo.get_by_id.return_value = {"product_type": "冷冻网带"}
        patcher_mr = patch('models.quality_rule.QualityRuleDAO.get_matching_rules',
                           return_value=[{**SAMPLE_DICT_ROW, "id": 5, "enabled": 1}])
        patcher_mr.start()
        patcher_items = patch('models.quality_rule.QualityRuleDAO.get_rule_items',
                              return_value=[{
                                  "id": 1, "inspection_item": "宽度检查",
                                  "check_formula": "", "tolerance": ""
                              }])
        patcher_items.start()
        try:
            from models.quality_rule import QualityRuleDAO
            result = QualityRuleDAO.evaluate_quality_rules(1, {})
            assert result["passed"] is True
        finally:
            patcher_order.stop()
            patcher_mr.stop()
            patcher_items.stop()

    def test_tolerance_format_exception(self, cursor, mock_conn):
        """公差格式异常时 is_passed=True"""
        patcher_order = patch('models.order.OrderDAO')
        mo = patcher_order.start()
        mo.get_by_id.return_value = {"product_type": "冷冻网带", "width": 100}
        patcher_mr = patch('models.quality_rule.QualityRuleDAO.get_matching_rules',
                           return_value=[{**SAMPLE_DICT_ROW, "id": 5, "enabled": 1}])
        patcher_mr.start()
        patcher_items = patch('models.quality_rule.QualityRuleDAO.get_rule_items',
                              return_value=[{
                                  "id": 1, "inspection_item": "宽度检查",
                                  "check_formula": "{宽度}*1.1", "tolerance": "invalid"
                              }])
        patcher_items.start()
        patcher_calc = patch('models.process_calc_rule.ProcessCalcEngine._calc_expr',
                             return_value=105.0)
        patcher_calc.start()
        try:
            from models.quality_rule import QualityRuleDAO
            result = QualityRuleDAO.evaluate_quality_rules(1, {"宽度检查": "200"})
            assert result["passed"] is True  # 异常时 is_passed=True
        finally:
            patcher_order.stop()
            patcher_mr.stop()
            patcher_items.stop()
            patcher_calc.stop()

    def test_order_data_field_fallback(self, cursor, mock_conn):
        """订单字段回退"""
        patcher_order = patch('models.order.OrderDAO')
        mo = patcher_order.start()
        # 订单有中文字段
        mo.get_by_id.return_value = {"product_type": "冷冻网带", "宽度": 200, "长度": 300}
        patcher_mr = patch('models.quality_rule.QualityRuleDAO.get_matching_rules',
                           return_value=[{**SAMPLE_DICT_ROW, "id": 5, "enabled": 1}])
        patcher_mr.start()
        patcher_items = patch('models.quality_rule.QualityRuleDAO.get_rule_items',
                              return_value=[{
                                  "id": 1, "inspection_item": "宽度检查",
                                  "check_formula": "", "tolerance": ""
                              }])
        patcher_items.start()
        try:
            from models.quality_rule import QualityRuleDAO
            result = QualityRuleDAO.evaluate_quality_rules(1, {"宽度检查": "200"})
            assert result["passed"] is True
        finally:
            patcher_order.stop()
            patcher_mr.stop()
            patcher_items.stop()

    def test_measured_str_exception(self, cursor, mock_conn):
        """实测值无法转 float → ValueError → measured=0 (覆盖 375-376)"""
        patcher_order = patch('models.order.OrderDAO')
        mo = patcher_order.start()
        mo.get_by_id.return_value = {"product_type": "冷冻网带", "width": 100}
        patcher_mr = patch('models.quality_rule.QualityRuleDAO.get_matching_rules',
                           return_value=[{**SAMPLE_DICT_ROW, "id": 5, "enabled": 1}])
        patcher_mr.start()
        patcher_items = patch('models.quality_rule.QualityRuleDAO.get_rule_items',
                              return_value=[{
                                  "id": 1, "inspection_item": "宽度检查",
                                  "check_formula": "{宽度}*1.1", "tolerance": ""
                              }])
        patcher_items.start()
        patcher_calc = patch('models.process_calc_rule.ProcessCalcEngine._calc_expr',
                             return_value=105.0)
        patcher_calc.start()
        try:
            from models.quality_rule import QualityRuleDAO
            result = QualityRuleDAO.evaluate_quality_rules(1, {"宽度检查": "abc"})
            assert result["passed"] is True
            assert result["record_items"][0]["measured_value"] == "abc"
        finally:
            patcher_order.stop()
            patcher_mr.stop()
            patcher_items.stop()
            patcher_calc.stop()


# ===================== init_default_rules 测试 =====================


def test_init_default_rules_already_has_data(cursor, mock_conn):
    """表非空时直接返回"""
    mock_conn.cursor.return_value.fetchone.return_value = [3]
    from models.quality_rule import QualityRuleDAO
    QualityRuleDAO.init_default_rules()
    cursor.execute.assert_called_once_with("SELECT COUNT(*) FROM quality_rules")


def test_init_default_rules_inserts_defaults(cursor, mock_conn):
    """表为空时插入 3 条默认规则"""
    mock_conn.cursor.return_value.fetchone.return_value = [0]
    from models.quality_rule import QualityRuleDAO
    QualityRuleDAO.init_default_rules()
    assert cursor.execute.call_count == 4  # 1 SELECT + 3 INSERT
    last_call_args = cursor.execute.call_args_list[-1]
    assert "终检" in str(last_call_args)
    mock_conn.commit.assert_called_once()


def test_init_default_rules_exception_rollback(cursor, mock_conn):
    """INSERT 异常时回滚"""
    mock_conn.cursor.return_value.fetchone.return_value = [0]
    cursor.execute.side_effect = [None, Exception("DB error")]
    from models.quality_rule import QualityRuleDAO
    QualityRuleDAO.init_default_rules()
    mock_conn.rollback.assert_called_once()
    assert cursor.execute.call_count >= 2


def test_init_default_rules_cursor_none(cursor, mock_conn):
    """cursor 为 None 时 finally 安全处理"""
    mock_conn.cursor.side_effect = Exception("No cursor")
    from models.quality_rule import QualityRuleDAO
    QualityRuleDAO.init_default_rules()
    mock_conn.rollback.assert_called_once()
    mock_conn.close.assert_called_once()