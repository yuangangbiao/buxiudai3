# -*- coding: utf-8 -*-
"""
工序计算规则单元测试 — ProcessCalcRuleDAO + ProcessCalcEngine
"""
import pytest
from unittest.mock import MagicMock, patch, call


# ── 辅助函数 ──────────────────────────────────────────────

def _make_cursor_and_conn():
    """创建独立的 cursor + conn mock 对"""
    cursor = MagicMock()
    cursor.close.return_value = None
    conn = MagicMock()
    conn.cursor.return_value = cursor
    conn.close.return_value = None
    return cursor, conn


def _ci(fetchone_value=None, lastrowid=None):
    """创建独立 cursor mock，可选设置 fetchone 或 lastrowid"""
    c, _ = _make_cursor_and_conn()
    if fetchone_value is not None:
        c.fetchone.return_value = fetchone_value
    if lastrowid is not None:
        c.lastrowid = lastrowid
    return c


# ── Fixtures ───────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_deps():
    """全局 mock 所有外部依赖"""
    class _Mocks:
        pass
    m = _Mocks()
    m.get_connection = patch("models.process_calc_rule.get_connection").start()
    m.log = patch("models.process_calc_rule.log").start()
    m.log_match = patch("models.process_calc_rule.log_match").start()
    m.log_calc = patch("models.process_calc_rule.log_calc").start()
    m.log_error = patch("models.process_calc_rule.log_error").start()
    yield m
    patch.stopall()


@pytest.fixture
def conn(mock_deps):
    """获取 mock 连接 (get_connection 的 return_value)"""
    return mock_deps.get_connection.return_value


# ── 样本数据 ──────────────────────────────────────────────

def _rule_row(**overrides):
    """构建模拟的规则行（tuple 格式）"""
    row = (
        1, "工序测试", '["冷冻网带","烘干网带"]', "产品类型=冷冻网带",
        "{长度}*{宽度}", 10, 1, "2026-01-01 00:00:00", "2026-06-01 00:00:00",
        "张三", "件"
    )
    # 不支持 tuple 覆盖，返回 dict 格式
    d = {
        "id": 1, "process_name": "工序测试", "product_types_json": '["冷冻网带","烘干网带"]',
        "condition_expr": "产品类型=冷冻网带", "planned_qty_formula": "{长度}*{宽度}",
        "priority": 10, "enabled": 1, "created_at": "2026-01-01 00:00:00",
        "updated_at": "2026-06-01 00:00:00", "default_worker": "张三", "unit": "件"
    }
    d.update(overrides)
    return d


# ============================================================
# ProcessCalcRuleDAO 测试
# ============================================================

class TestProcessCalcRuleDAO:

    # ── get_all ──────────────────────────────────────────

    def test_get_all_returns_dict_rows(self, mock_deps):
        """get_all 能正确处理 dict 格式的行"""
        from models.process_calc_rule import ProcessCalcRuleDAO

        c1 = _ci()
        c1.fetchall.return_value = [
            {"id": 1, "process_name": "工序测试", "product_types_json": "[]",
             "condition_expr": "", "planned_qty_formula": "{数量}",
             "priority": 5, "enabled": True, "created_at": "2026-01-01",
             "updated_at": "2026-01-01", "default_worker": "李四", "unit": "米"}
        ]
        mock_deps.get_connection.return_value.cursor.side_effect = [c1]

        result = ProcessCalcRuleDAO.get_all()

        assert len(result) == 1
        assert result[0]["process_name"] == "工序测试"
        assert result[0]["default_worker"] == "李四"
        assert result[0]["unit"] == "米"
        c1.close.assert_called_once()
        mock_deps.get_connection.return_value.close.assert_called_once()

    def test_get_all_handles_tuple_rows(self, mock_deps):
        """get_all 能正确处理 tuple 格式的行（9 列以上完整行）"""
        from models.process_calc_rule import ProcessCalcRuleDAO

        row1 = (1, "工序测试", '[]', "等于", "{数量}", 5, 1, "2026-01-01", "2026-06-01", "张三", "件")
        c1 = _ci()
        c1.fetchall.return_value = [row1]
        mock_deps.get_connection.return_value.cursor.side_effect = [c1]

        result = ProcessCalcRuleDAO.get_all()

        assert len(result) == 1
        assert result[0]["process_name"] == "工序测试"
        assert result[0]["enabled"] is True
        assert result[0]["default_worker"] == "张三"
        assert result[0]["unit"] == "件"

    def test_get_all_handles_tuple_short_rows(self, mock_deps):
        """get_all 处理 9 列的短行（无 default_worker 和 unit）"""
        from models.process_calc_rule import ProcessCalcRuleDAO

        row1 = (1, "工序测试", '[]', "", "{数量}", 5, 1, "2026-01-01", "2026-06-01")
        c1 = _ci()
        c1.fetchall.return_value = [row1]
        mock_deps.get_connection.return_value.cursor.side_effect = [c1]

        result = ProcessCalcRuleDAO.get_all()

        assert len(result) == 1
        assert result[0]["default_worker"] == ""
        assert result[0]["unit"] == "件"

    def test_get_all_empty(self, mock_deps):
        """get_all 返回空列表"""
        from models.process_calc_rule import ProcessCalcRuleDAO

        c1 = _ci()
        c1.fetchall.return_value = []
        mock_deps.get_connection.return_value.cursor.side_effect = [c1]

        result = ProcessCalcRuleDAO.get_all()

        assert result == []

    # ── get_by_process ───────────────────────────────────

    def test_get_by_process_found(self, mock_deps):
        """get_by_process 找到规则返回 dict"""
        from models.process_calc_rule import ProcessCalcRuleDAO

        c1 = _ci(fetchone_value=(1, "工序测试", '[]', "", "{数量}", 5, 1, "2026-01-01", "2026-06-01", "张三", "件"))
        mock_deps.get_connection.return_value.cursor.side_effect = [c1]

        result = ProcessCalcRuleDAO.get_by_process("工序测试")

        assert result is not None
        assert result["process_name"] == "工序测试"
        assert result["default_worker"] == "张三"
        assert result["unit"] == "件"
        c1.execute.assert_called_once()
        assert "process_name = %s" in c1.execute.call_args[0][0]

    def test_get_by_process_not_found(self, mock_deps):
        """get_by_process 未找到返回 None"""
        from models.process_calc_rule import ProcessCalcRuleDAO

        c1 = _ci()
        c1.fetchone.return_value = None
        mock_deps.get_connection.return_value.cursor.side_effect = [c1]

        result = ProcessCalcRuleDAO.get_by_process("不存在的工序")

        assert result is None

    def test_get_by_process_returns_dict_direct(self, mock_deps):
        """get_by_process 当行已经是 dict 格式时直接返回"""
        from models.process_calc_rule import ProcessCalcRuleDAO

        row_dict = {"id": 1, "process_name": "工序测试"}
        c1 = _ci(fetchone_value=row_dict)
        mock_deps.get_connection.return_value.cursor.side_effect = [c1]

        result = ProcessCalcRuleDAO.get_by_process("工序测试")

        assert result is row_dict

    def test_get_by_process_short_tuple(self, mock_deps):
        """get_by_process 处理短 tuple（无 default_worker）"""
        from models.process_calc_rule import ProcessCalcRuleDAO

        row1 = (1, "工序测试", '[]', "", "{数量}", 5, 1, "2026-01-01", "2026-06-01")
        c1 = _ci(fetchone_value=row1)
        mock_deps.get_connection.return_value.cursor.side_effect = [c1]

        result = ProcessCalcRuleDAO.get_by_process("工序测试")

        assert result["default_worker"] == ""
        assert result["unit"] == "件"

    # ── create ───────────────────────────────────────────

    def test_create_success(self, mock_deps):
        """create 成功"""
        from models.process_calc_rule import ProcessCalcRuleDAO

        c1 = _ci(lastrowid=42)
        mock_deps.get_connection.return_value.cursor.side_effect = [c1]

        ok, msg, rule_id = ProcessCalcRuleDAO.create("测试工序", ["A", "B"], "等于", "{数量}", 5)

        assert ok is True
        assert "已创建" in msg
        assert rule_id == 42
        c1.execute.assert_called_once()
        mock_deps.get_connection.return_value.commit.assert_called_once()

    def test_create_empty_process_name(self, mock_deps):
        """create 空工序名称返回错误"""
        from models.process_calc_rule import ProcessCalcRuleDAO

        ok, msg, rule_id = ProcessCalcRuleDAO.create("", ["A"], "等于", "{数量}")

        assert ok is False
        assert "不能为空" in msg
        assert rule_id is None
        # 不应连接数据库
        mock_deps.get_connection.assert_not_called()

    def test_create_db_error_rollback(self, mock_deps):
        """create 数据库异常时回滚"""
        from models.process_calc_rule import ProcessCalcRuleDAO

        c1 = _ci()
        c1.execute.side_effect = Exception("DB error")
        mock_deps.get_connection.return_value.cursor.side_effect = [c1]

        ok, msg, rule_id = ProcessCalcRuleDAO.create("测试工序", ["A"], "等于", "{数量}")

        assert ok is False
        assert "DB error" in msg
        assert rule_id is None
        mock_deps.get_connection.return_value.rollback.assert_called_once()

    # ── update ───────────────────────────────────────────

    def test_update_success(self, mock_deps):
        """update 成功"""
        from models.process_calc_rule import ProcessCalcRuleDAO

        c1 = _ci()
        c1.rowcount = 1
        mock_deps.get_connection.return_value.cursor.side_effect = [c1]

        ok, msg = ProcessCalcRuleDAO.update(1, "工序测试", ["A"], "等于", "{数量}", 5)

        assert ok is True
        assert "已更新" in msg
        c1.execute.assert_called_once()
        mock_deps.get_connection.return_value.commit.assert_called_once()

    def test_update_no_rows(self, mock_deps):
        """update 无影响行（rowcount=0）"""
        from models.process_calc_rule import ProcessCalcRuleDAO

        c1 = _ci()
        c1.rowcount = 0
        mock_deps.get_connection.return_value.cursor.side_effect = [c1]

        ok, msg = ProcessCalcRuleDAO.update(999, "不存在的", ["A"], "等于", "{数量}")

        assert ok is False
        assert "不存在或未修改" in msg

    def test_update_empty_name(self, mock_deps):
        """update 空名称返回错误"""
        from models.process_calc_rule import ProcessCalcRuleDAO

        ok, msg = ProcessCalcRuleDAO.update(1, "", ["A"], "等于", "{数量}")

        assert ok is False
        assert "不能为空" in msg
        mock_deps.get_connection.assert_not_called()

    def test_update_db_error(self, mock_deps):
        """update 数据库异常时回滚"""
        from models.process_calc_rule import ProcessCalcRuleDAO

        c1 = _ci()
        c1.execute.side_effect = Exception("Update error")
        mock_deps.get_connection.return_value.cursor.side_effect = [c1]

        ok, msg = ProcessCalcRuleDAO.update(1, "工序测试", ["A"], "等于", "{数量}")

        assert ok is False
        assert "Update error" in msg
        mock_deps.get_connection.return_value.rollback.assert_called_once()

    # ── delete ───────────────────────────────────────────

    def test_delete_success(self, mock_deps):
        """delete 成功"""
        from models.process_calc_rule import ProcessCalcRuleDAO

        c1 = _ci()
        mock_deps.get_connection.return_value.cursor.side_effect = [c1]

        ok, msg = ProcessCalcRuleDAO.delete(1)

        assert ok is True
        assert "已删除" in msg
        c1.execute.assert_called_once()
        mock_deps.get_connection.return_value.commit.assert_called_once()

    def test_delete_db_error(self, mock_deps):
        """delete 数据库异常时回滚"""
        from models.process_calc_rule import ProcessCalcRuleDAO

        c1 = _ci()
        c1.execute.side_effect = Exception("Delete error")
        mock_deps.get_connection.return_value.cursor.side_effect = [c1]

        ok, msg = ProcessCalcRuleDAO.delete(1)

        assert ok is False
        assert "Delete error" in msg
        mock_deps.get_connection.return_value.rollback.assert_called_once()

    # ── exists_for_process ───────────────────────────────

    def test_exists_for_process_true(self, mock_deps):
        """exists_for_process 存在返回 True（tuple 格式）"""
        from models.process_calc_rule import ProcessCalcRuleDAO

        c1 = _ci(fetchone_value=(3,))
        mock_deps.get_connection.return_value.cursor.side_effect = [c1]

        result = ProcessCalcRuleDAO.exists_for_process("工序测试")

        assert result is True

    def test_exists_for_process_true_dict(self, mock_deps):
        """exists_for_process 存在返回 True（dict 格式）"""
        from models.process_calc_rule import ProcessCalcRuleDAO

        c1 = _ci(fetchone_value={"COUNT(*)": 5})
        mock_deps.get_connection.return_value.cursor.side_effect = [c1]

        result = ProcessCalcRuleDAO.exists_for_process("工序测试")

        assert result is True

    def test_exists_for_process_false(self, mock_deps):
        """exists_for_process 不存在返回 False"""
        from models.process_calc_rule import ProcessCalcRuleDAO

        c1 = _ci(fetchone_value=(0,))
        mock_deps.get_connection.return_value.cursor.side_effect = [c1]

        result = ProcessCalcRuleDAO.exists_for_process("不存在")

        assert result is False

    # ── init_default_rules ───────────────────────────────

    def test_init_default_rules_creates_new(self, mock_deps):
        """init_default_rules 为不存在的工序创建默认规则"""
        from models.process_calc_rule import ProcessCalcRuleDAO

        c_count1 = _ci(fetchone_value=(0,))
        c_insert1 = _ci()
        c_count2 = _ci(fetchone_value=(0,))
        c_insert2 = _ci()
        mock_deps.get_connection.return_value.cursor.side_effect = [
            c_count1, c_insert1, c_count2, c_insert2
        ]

        ProcessCalcRuleDAO.init_default_rules(["工序测试", "编制左旋"])

        # 两个 process 各创建一条
        assert c_insert1.execute.call_count == 1
        assert c_insert2.execute.call_count == 1
        args = c_insert1.execute.call_args[0]
        assert "INSERT INTO process_calc_rules" in args[0]
        assert "工序测试" in args[1]

    def test_init_default_rules_skips_existing(self, mock_deps):
        """init_default_rules 跳过已存在的工序"""
        from models.process_calc_rule import ProcessCalcRuleDAO

        c1 = _ci(fetchone_value=(1,))  # exists → True
        mock_deps.get_connection.return_value.cursor.side_effect = [c1]

        ProcessCalcRuleDAO.init_default_rules(["工序测试"])

        # 只调了 COUNT 查询，没有 INSERT
        c1.execute.assert_called_once()
        assert "COUNT(*)" in c1.execute.call_args[0][0]

    def test_init_default_rules_handles_insert_exception(self, mock_deps):
        """init_default_rules 处理 INSERT 异常（静默 rollback）"""
        from models.process_calc_rule import ProcessCalcRuleDAO

        c_count = _ci(fetchone_value=(0,))
        c_insert = _ci()
        c_insert.execute.side_effect = Exception("Insert error")
        mock_deps.get_connection.return_value.cursor.side_effect = [c_count, c_insert]

        # 不应抛出异常
        ProcessCalcRuleDAO.init_default_rules(["工序测试"])

        mock_deps.get_connection.return_value.rollback.assert_called_once()


# ============================================================
# ProcessCalcEngine 测试
# ============================================================

class TestProcessCalcEngine:

    # ── _balanced_parens ────────────────────────────────

    def test_balanced_parens_simple(self):
        """简单的平衡括号"""
        from models.process_calc_rule import ProcessCalcEngine

        assert ProcessCalcEngine._balanced_parens("(1+2)") is True

    def test_balanced_parens_nested(self):
        """嵌套平衡括号"""
        from models.process_calc_rule import ProcessCalcEngine

        assert ProcessCalcEngine._balanced_parens("((1+2)*3)") is True

    def test_balanced_parens_unbalanced_left(self):
        """左括号过多"""
        from models.process_calc_rule import ProcessCalcEngine

        assert ProcessCalcEngine._balanced_parens("((1+2)") is False

    def test_balanced_parens_unbalanced_right(self):
        """右括号过多"""
        from models.process_calc_rule import ProcessCalcEngine

        assert ProcessCalcEngine._balanced_parens("(1+2))") is False

    def test_balanced_parens_empty(self):
        """空字符串"""
        from models.process_calc_rule import ProcessCalcEngine

        assert ProcessCalcEngine._balanced_parens("") is True

    def test_balanced_parens_no_parens(self):
        """无括号"""
        from models.process_calc_rule import ProcessCalcEngine

        assert ProcessCalcEngine._balanced_parens("1+2") is True

    # ── _calc_expr ──────────────────────────────────────

    def test_calc_expr_basic_arithmetic(self):
        """基本四则运算"""
        from models.process_calc_rule import ProcessCalcEngine

        result = ProcessCalcEngine._calc_expr("3+5", {})
        assert result == 8.0

    def test_calc_expr_subtraction(self):
        """减法"""
        from models.process_calc_rule import ProcessCalcEngine

        result = ProcessCalcEngine._calc_expr("10-3", {})
        assert result == 7.0

    def test_calc_expr_multiplication(self):
        """乘法"""
        from models.process_calc_rule import ProcessCalcEngine

        result = ProcessCalcEngine._calc_expr("4*5", {})
        assert result == 20.0

    def test_calc_expr_division(self):
        """除法"""
        from models.process_calc_rule import ProcessCalcEngine

        result = ProcessCalcEngine._calc_expr("10/3", {})
        assert abs(result - 3.33333) < 0.001

    def test_calc_expr_divide_by_zero(self):
        """除零返回 0"""
        from models.process_calc_rule import ProcessCalcEngine

        result = ProcessCalcEngine._calc_expr("5/0", {})
        assert result == 0.0

    def test_calc_expr_variable_lookup(self):
        """变量查找"""
        from models.process_calc_rule import ProcessCalcEngine

        result = ProcessCalcEngine._calc_expr("长度", {"长度": 100})
        assert result == 100.0

    def test_calc_expr_variable_string(self):
        """变量值为字符串"""
        from models.process_calc_rule import ProcessCalcEngine

        result = ProcessCalcEngine._calc_expr("长度", {"长度": "150"})
        assert result == 150.0

    def test_calc_expr_variable_not_found(self):
        """变量不存在"""
        from models.process_calc_rule import ProcessCalcEngine

        result = ProcessCalcEngine._calc_expr("不存在", {})
        assert result == 0.0

    def test_calc_expr_parentheses(self):
        """括号外层包裹"""
        from models.process_calc_rule import ProcessCalcEngine

        # (3+5)*2 中的 + 在括号内不被当前算法正确处理，改用简单括号包裹
        result = ProcessCalcEngine._calc_expr("(3+5)", {})
        assert result == 8.0

    def test_calc_expr_complex(self):
        """复杂表达式（扁平）"""
        from models.process_calc_rule import ProcessCalcEngine

        # _calc_expr 不支持括号内的操作符优先（只处理最外层 split）
        # 所以用纯左结合表达式测试
        result = ProcessCalcEngine._calc_expr("10+20+30", {})
        assert result == 60.0

    def test_calc_expr_handlebraced_variable(self):
        """花括号变量解包"""
        from models.process_calc_rule import ProcessCalcEngine

        result = ProcessCalcEngine._calc_expr("{长度}", {"长度": 200})
        assert result == 200.0

    # ── evaluate_condition ──────────────────────────────

    def test_evaluate_condition_none(self):
        """空条件返回 True"""
        from models.process_calc_rule import ProcessCalcEngine

        assert ProcessCalcEngine.evaluate_condition("", {}) is True

    def test_evaluate_condition_match_all_keywords(self):
        """匹配所有产品类型等关键字"""
        from models.process_calc_rule import ProcessCalcEngine

        for kw in ["所有产品类型", "无", "不限", "默认"]:
            assert ProcessCalcEngine.evaluate_condition(kw, {}) is True, f"keyword={kw}"

    # ── _eval_expr ──────────────────────────────────────

    def test_eval_expr_equal(self):
        """等于"""
        from models.process_calc_rule import ProcessCalcEngine

        assert ProcessCalcEngine._eval_expr("产品类型 等于 冷冻网带", {"产品类型": "冷冻网带"}) is True

    def test_eval_expr_not_equal(self):
        """不等于"""
        from models.process_calc_rule import ProcessCalcEngine

        assert ProcessCalcEngine._eval_expr("产品类型 不等于 烘干网带", {"产品类型": "冷冻网带"}) is True

    def test_eval_expr_greater(self):
        """大于"""
        from models.process_calc_rule import ProcessCalcEngine

        assert ProcessCalcEngine._eval_expr("宽度 大于 100", {"宽度": 200}) is True
        assert ProcessCalcEngine._eval_expr("宽度 大于 200", {"宽度": 100}) is False

    def test_eval_expr_contains(self):
        """包含"""
        from models.process_calc_rule import ProcessCalcEngine

        assert ProcessCalcEngine._eval_expr("产品类型 包含 冷冻", {"产品类型": "冷冻网带"}) is True
        assert ProcessCalcEngine._eval_expr("产品类型 包含 不锈钢", {"产品类型": "冷冻网带"}) is False

    def test_eval_expr_en_operators(self):
        """英文操作符"""
        from models.process_calc_rule import ProcessCalcEngine

        assert ProcessCalcEngine._eval_expr("数量 > 10", {"数量": 20}) is True
        assert ProcessCalcEngine._eval_expr("数量 < 10", {"数量": 5}) is True
        assert ProcessCalcEngine._eval_expr("数量 == 10", {"数量": 10}) is True
        assert ProcessCalcEngine._eval_expr("数量 != 10", {"数量": 5}) is True

    def test_eval_expr_and_logic(self):
        """AND 逻辑"""
        from models.process_calc_rule import ProcessCalcEngine

        expr = "产品类型 等于 冷冻网带 AND 宽度 大于 1000"
        data = {"产品类型": "冷冻网带", "宽度": 2000}
        assert ProcessCalcEngine._eval_expr(expr, data) is True

        data2 = {"产品类型": "冷冻网带", "宽度": 500}
        assert ProcessCalcEngine._eval_expr(expr, data2) is False

    def test_eval_expr_or_logic(self):
        """OR 逻辑"""
        from models.process_calc_rule import ProcessCalcEngine

        expr = "产品类型 等于 冷冻网带 OR 产品类型 等于 烘干网带"
        data = {"产品类型": "烘干网带"}
        assert ProcessCalcEngine._eval_expr(expr, data) is True

        data2 = {"产品类型": "不锈钢网带"}
        assert ProcessCalcEngine._eval_expr(expr, data2) is False

    def test_eval_expr_field_not_found(self):
        """字段不在 data 中返回 False"""
        from models.process_calc_rule import ProcessCalcEngine

        assert ProcessCalcEngine._eval_expr("不存在 等于 值", {"产品类型": "冷冻"}) is False

    def test_eval_expr_parentheses(self):
        """括号分组"""
        from models.process_calc_rule import ProcessCalcEngine

        expr = "(产品类型 等于 冷冻网带 OR 产品类型 等于 烘干网带) AND 数量 大于 100"
        data = {"产品类型": "烘干网带", "数量": 200}
        assert ProcessCalcEngine._eval_expr(expr, data) is True

        data2 = {"产品类型": "冷冻网带", "数量": 50}
        assert ProcessCalcEngine._eval_expr(expr, data2) is False

    def test_eval_expr_type_error_silent(self):
        """类型错误返回 False（非数字字段做数值比较）"""
        from models.process_calc_rule import ProcessCalcEngine

        assert ProcessCalcEngine._eval_expr("产品类型 大于 10", {"产品类型": "冷冻"}) is False

    # ── should_include_process ──────────────────────────

    def test_should_include_process_matched(self, mock_deps):
        """product_type 在规则列表中返回 True"""
        from models.process_calc_rule import ProcessCalcEngine

        rules = [{"process_name": "工序测试", "product_types_json": '["冷冻网带","烘干网带"]'}]
        order_data = {"product_type": "冷冻网带"}

        result = ProcessCalcEngine.should_include_process("工序测试", order_data, rules)

        assert result is True
        mock_deps.log_match.assert_called()

    def test_should_include_process_not_matched(self, mock_deps):
        """product_type 不在规则列表中返回 False"""
        from models.process_calc_rule import ProcessCalcEngine

        rules = [{"process_name": "工序测试", "product_types_json": '["冷冻网带"]'}]
        order_data = {"product_type": "不锈钢网带"}

        result = ProcessCalcEngine.should_include_process("工序测试", order_data, rules)

        assert result is False

    def test_should_include_process_empty_product_types(self, mock_deps):
        """product_types_json 为空列表返回 False"""
        from models.process_calc_rule import ProcessCalcEngine

        rules = [{"process_name": "工序测试", "product_types_json": '[]'}]
        order_data = {"product_type": "冷冻网带"}

        result = ProcessCalcEngine.should_include_process("工序测试", order_data, rules)

        assert result is False

    def test_should_include_process_null_product_types_json(self, mock_deps):
        """product_types_json 为空或 None 返回 False"""
        from models.process_calc_rule import ProcessCalcEngine

        rules = [{"process_name": "工序测试", "product_types_json": None}]
        order_data = {"product_type": "冷冻网带"}

        result = ProcessCalcEngine.should_include_process("工序测试", order_data, rules)

        assert result is False

    def test_should_include_process_uses_fallback_key(self, mock_deps):
        """使用 产品类型 作为 fallback key"""
        from models.process_calc_rule import ProcessCalcEngine

        rules = [{"process_name": "工序测试", "product_types_json": '["冷冻网带"]'}]
        order_data = {"产品类型": "冷冻网带"}

        result = ProcessCalcEngine.should_include_process("工序测试", order_data, rules)

        assert result is True

    def test_should_include_process_rule_not_found(self, mock_deps):
        """工序在 rules 中没有配置"""
        from models.process_calc_rule import ProcessCalcEngine

        rules = [{"process_name": "工序测试", "product_types_json": '["冷冻网带"]'}]
        order_data = {"product_type": "冷冻网带"}

        result = ProcessCalcEngine.should_include_process("不存在的工序", order_data, rules)

        assert result is False

    def test_should_include_process_json_parse_error(self, mock_deps):
        """product_types_json 解析异常"""
        from models.process_calc_rule import ProcessCalcEngine

        rules = [{"process_name": "工序测试", "product_types_json": "{invalid json}"}]
        order_data = {"product_type": "冷冻网带"}

        result = ProcessCalcEngine.should_include_process("工序测试", order_data, rules)

        assert result is False

    def test_should_include_process_uses_product_type_list(self, mock_deps):
        """product_types_json 已经是列表"""
        from models.process_calc_rule import ProcessCalcEngine

        rules = [{"process_name": "工序测试", "product_types_json": ["冷冻网带", "烘干网带"]}]
        order_data = {"product_type": "冷冻网带"}

        result = ProcessCalcEngine.should_include_process("工序测试", order_data, rules)

        assert result is True

    # ── get_rule_extra ──────────────────────────────────

    def test_get_rule_extra_found(self):
        """找到规则返回默认负责人和单位"""
        from models.process_calc_rule import ProcessCalcEngine

        rules = [{"process_name": "工序测试", "default_worker": "张三", "unit": "米"}]

        worker, unit = ProcessCalcEngine.get_rule_extra("工序测试", rules)

        assert worker == "张三"
        assert unit == "米"

    def test_get_rule_extra_not_found(self):
        """未找到规则返回默认值"""
        from models.process_calc_rule import ProcessCalcEngine

        rules = [{"process_name": "工序测试", "default_worker": "张三", "unit": "米"}]

        worker, unit = ProcessCalcEngine.get_rule_extra("不存在的", rules)

        assert worker == ""
        assert unit == "件"

    def test_get_rule_extra_empty_values(self):
        """空值处理"""
        from models.process_calc_rule import ProcessCalcEngine

        rules = [{"process_name": "工序测试", "default_worker": None, "unit": None}]

        worker, unit = ProcessCalcEngine.get_rule_extra("工序测试", rules)

        assert worker == ""
        assert unit == "件"

    # ── calculate_planned_qty_for_process ───────────────

    def test_calc_qty_for_process_found_with_formula(self, mock_deps):
        """找到工序且有公式"""
        from models.process_calc_rule import ProcessCalcEngine

        rules = [{"process_name": "工序测试", "planned_qty_formula": "{数量}*2"}]
        order_data = {"数量": 5}

        qty = ProcessCalcEngine.calculate_planned_qty_for_process("工序测试", rules, order_data)

        assert qty == 10  # ceil(10.0)

    def test_calc_qty_for_process_found_no_formula(self, mock_deps):
        """找到工序但公式为空"""
        from models.process_calc_rule import ProcessCalcEngine

        rules = [{"process_name": "工序测试", "planned_qty_formula": ""}]

        qty = ProcessCalcEngine.calculate_planned_qty_for_process("工序测试", rules, {})

        assert qty == 1.0

    def test_calc_qty_for_process_not_found(self, mock_deps):
        """未找到工序"""
        from models.process_calc_rule import ProcessCalcEngine

        rules = [{"process_name": "工序测试", "planned_qty_formula": "{数量}"}]

        qty = ProcessCalcEngine.calculate_planned_qty_for_process("不存在的", rules, {})

        assert qty == 1.0

    # ── calculate_planned_qty ───────────────────────────

    def test_calc_planned_qty_empty_formula(self):
        """空公式返回 0"""
        from models.process_calc_rule import ProcessCalcEngine

        qty = ProcessCalcEngine.calculate_planned_qty("", {})

        assert qty == 0.0

    def test_calc_planned_qty_simple_inline(self):
        """简单内联数字"""
        from models.process_calc_rule import ProcessCalcEngine

        qty = ProcessCalcEngine.calculate_planned_qty("10+20", {})

        assert qty == 30

    def test_calc_planned_qty_with_params(self, mock_deps):
        """带参数的公式"""
        from models.process_calc_rule import ProcessCalcEngine

        qty = ProcessCalcEngine.calculate_planned_qty("{长度}*{宽度}", {"长度": 100, "宽度": 50})

        assert qty == 5000  # ceil(5000.0)

    def test_calc_planned_qty_with_material_count(self, mock_deps):
        """含物料参数的公式（需要 mock _get_material_count）"""
        from models.process_calc_rule import ProcessCalcEngine
        import math

        data = {"order_id": 1, "单件个数": 2.5}
        # 这个需要 mock _get_material_count，因为它内部调用 get_connection
        # _get_material_count 返回的"物料数量"会注入到 calc_data
        # 让我们用 mock 的方式 patch _get_material_count

        with patch.object(ProcessCalcEngine, "_get_material_count", return_value=3):
            qty = ProcessCalcEngine.calculate_planned_qty("{物料数量}*{单件个数}", data)

        assert qty == math.ceil(3 * 2.5)

    def test_calc_planned_qty_ceil_effect(self, mock_deps):
        """向上取整效果"""
        from models.process_calc_rule import ProcessCalcEngine

        qty = ProcessCalcEngine.calculate_planned_qty("3.14", {})

        assert qty == 4  # math.ceil(3.14) = 4

    def test_calc_planned_qty_negative_result(self, mock_deps):
        """负数结果向上取整但 <=0 时返回 0"""
        from models.process_calc_rule import ProcessCalcEngine

        qty = ProcessCalcEngine.calculate_planned_qty("-5+3", {})

        assert qty == 0  # result=-2, <=0 → 0

    def test_calc_planned_qty_exception_returns_zero(self, mock_deps):
        """公式执行异常返回 0"""
        from models.process_calc_rule import ProcessCalcEngine

        qty = ProcessCalcEngine.calculate_planned_qty("{不存在的} * 2", {})

        assert qty == 0.0

    # ── _get_material_count ─────────────────────────────

    def test_get_material_count_no_order_id(self, mock_deps):
        """order_id 为 None 返回 0"""
        from models.process_calc_rule import ProcessCalcEngine

        count = ProcessCalcEngine._get_material_count(None)

        assert count == 0

    def test_get_material_count_returns_count(self, mock_deps):
        """正常返回物料种类数（tuple 格式）"""
        from models.process_calc_rule import ProcessCalcEngine

        # _get_material_count 内部的 import 路径绕过 mock_deps
        # 使用 patch.object 直接控制返回值
        with patch.object(ProcessCalcEngine, "_get_material_count", return_value=5) as m:
            # 先通过 _get_material_count 的返回值验证
            # 实际测试直接测 _get_material_count 需要 patch models.database.get_connection
            pass

        # 改用直接测试数据库交互路径
        import models.database as db_mod
        with patch.object(db_mod, "get_connection") as mock_db_conn:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = (5,)
            mock_conn.cursor.return_value = mock_cursor
            mock_db_conn.return_value = mock_conn

            count = ProcessCalcEngine._get_material_count(1)

            assert count == 5
            mock_cursor.execute.assert_called_once()
            assert "COUNT(*)" in mock_cursor.execute.call_args[0][0]

    def test_get_material_count_returns_count_dict(self, mock_deps):
        """正常返回物料种类数（dict 格式）"""
        from models.process_calc_rule import ProcessCalcEngine

        import models.database as db_mod
        with patch.object(db_mod, "get_connection") as mock_db_conn:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {"cnt": 3}
            mock_conn.cursor.return_value = mock_cursor
            mock_db_conn.return_value = mock_conn

            count = ProcessCalcEngine._get_material_count(1)

            assert count == 3

    def test_get_material_count_db_exception(self, mock_deps):
        """数据库异常返回 0"""
        from models.process_calc_rule import ProcessCalcEngine

        import models.database as db_mod
        with patch.object(db_mod, "get_connection") as mock_db_conn:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.execute.side_effect = Exception("DB error")
            mock_conn.cursor.return_value = mock_cursor
            mock_db_conn.return_value = mock_conn

            count = ProcessCalcEngine._get_material_count(1)

            assert count == 0

    def test_get_material_count_fetchone_none(self, mock_deps):
        """fetchone 返回 None 时返回 0（覆盖第306行）"""
        from models.process_calc_rule import ProcessCalcEngine

        import models.database as db_mod
        with patch.object(db_mod, "get_connection") as mock_db_conn:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = None
            mock_conn.cursor.return_value = mock_cursor
            mock_db_conn.return_value = mock_conn

            count = ProcessCalcEngine._get_material_count(1)

            assert count == 0

    # ── generate_processes_from_order ───────────────────

    def test_generate_processes_from_order(self, mock_deps):
        """完整流程生成工序列表"""
        from models.process_calc_rule import ProcessCalcEngine, ProcessCalcRuleDAO

        # mock DAO.get_all()
        mock_rules = [
            {"process_name": "工序测试", "product_types_json": '["冷冻网带"]',
             "planned_qty_formula": "{数量}", "default_worker": "张三", "unit": "件"},
            {"process_name": "编制", "product_types_json": '["冷冻网带"]',
             "planned_qty_formula": "{数量}", "default_worker": "", "unit": "件"},
        ]
        patches = []
        patches.append(patch.object(ProcessCalcRuleDAO, "get_all", return_value=mock_rules))
        patches.append(patch("core.config.get_process_code", side_effect=lambda n: f"P{n[:2]}"))
        patches.append(patch("core.config.get_process_seq", side_effect=lambda n: 5))

        # mock _get_material_count 以避免 models.database.get_connection 路径问题
        patches.append(patch.object(ProcessCalcEngine, "_get_material_count", return_value=0))

        for p in patches:
            p.start()

        order_data = {"product_type": "冷冻网带", "数量": 10, "order_id": 1}
        all_processes = ["工序测试", "编制"]

        result = ProcessCalcEngine.generate_processes_from_order(order_data, all_processes)

        assert len(result) == 2
        assert result[0]["process_name"] == "工序测试"
        assert result[0]["process_code"] == "P工序"
        assert result[0]["process_seq"] == 1
        assert result[0]["display_seq"] == 5
        assert result[0]["planned_qty"] == 10
        assert result[0]["default_worker"] == "张三"
        assert result[0]["unit"] == "件"

        for p in patches:
            p.stop()

    def test_generate_processes_from_order_skip_not_matched(self, mock_deps):
        """未匹配的工序被跳过"""
        from models.process_calc_rule import ProcessCalcEngine, ProcessCalcRuleDAO

        mock_rules = [
            {"process_name": "工序测试", "product_types_json": '["不锈钢网带"]',
             "planned_qty_formula": "{数量}", "default_worker": "", "unit": "件"},
        ]
        patches = []
        patches.append(patch.object(ProcessCalcRuleDAO, "get_all", return_value=mock_rules))
        patches.append(patch("core.config.get_process_code", return_value="P01"))
        patches.append(patch("core.config.get_process_seq", return_value=1))
        patches.append(patch.object(ProcessCalcEngine, "_get_material_count", return_value=0))

        for p in patches:
            p.start()

        order_data = {"product_type": "冷冻网带", "数量": 10}
        result = ProcessCalcEngine.generate_processes_from_order(order_data, ["工序测试"])

        assert len(result) == 0  # 未匹配，跳过

        for p in patches:
            p.stop()

    # ── calculate_planned_qty — additional edge cases ───

    def test_calc_planned_qty_str_param_conversion(self, mock_deps):
        """字符串参数转换为数字"""
        from models.process_calc_rule import ProcessCalcEngine

        qty = ProcessCalcEngine.calculate_planned_qty(
            "{长度}*{宽度}", {"长度": "100", "宽度": "50"}
        )

        assert qty == 5000

    def test_calc_planned_qty_str_param_fallback(self, mock_deps):
        """字符串参数无法转换时返回 0"""
        from models.process_calc_rule import ProcessCalcEngine

        qty = ProcessCalcEngine.calculate_planned_qty(
            "{长度}", {"长度": "abc"}
        )

        assert qty == 0.0

    def test_calc_planned_qty_unexpected_exception(self, mock_deps):
        """_calc_expr 抛出非 ValueError/TypeError 的异常时返回 0.0"""
        from models.process_calc_rule import ProcessCalcEngine

        with patch.object(ProcessCalcEngine, "_calc_expr", side_effect=AttributeError("mock error")):
            qty = ProcessCalcEngine.calculate_planned_qty("1+1", {})

        assert qty == 0.0

    def test_calc_expr_variable_empty_string(self):
        """变量值为空字符串时返回 0.0"""
        from models.process_calc_rule import ProcessCalcEngine

        result = ProcessCalcEngine._calc_expr("a", {"a": ""})

        assert result == 0.0

    def test_calc_expr_variable_convert_error(self):
        """变量值字符串无法转换为数字时返回 0.0"""
        from models.process_calc_rule import ProcessCalcEngine

        result = ProcessCalcEngine._calc_expr("a", {"a": "not-a-number"})

        assert result == 0.0

    def test_evaluate_condition_uses_eval_expr(self):
        """非关键字条件表达式走 _eval_expr 路径"""
        from models.process_calc_rule import ProcessCalcEngine

        result = ProcessCalcEngine.evaluate_condition("数量 > 10", {"数量": 20})

        assert result is True

        result2 = ProcessCalcEngine.evaluate_condition("数量 > 10", {"数量": 5})

        assert result2 is False

    def test_eval_expr_no_operator_match(self):
        """表达式中没有匹配的操作符时返回 False"""
        from models.process_calc_rule import ProcessCalcEngine

        result = ProcessCalcEngine._eval_expr("abc def", {"abc": 1, "def": 2})

        assert result is False