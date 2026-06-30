# -*- coding: utf-8 -*-
"""修复 test_quality_rule.py 的 TestUpdate 和 TestDelete"""
FILE = r"d:\yuan\不锈钢网带跟单3.0\tests\unit\models\test_quality_rule.py"

with open(FILE, "r", encoding="utf-8") as f:
    content = f.read()

# 1. TestUpdate - update 需要 rule_name, product_types, condition_expr, inspection_items
OLD_UPDATE_SUCCESS = """    def test_success(self):
        """更新成功"""
        self._mock_cursor.rowcount = 1
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.update(1, rule_name="规则B")
        assert result is True

    def test_exception_rollback(self):
        """异常回滚"""
        self._mock_cursor.execute.side_effect = Exception("DB error")
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.update(1, rule_name="规则B")
        assert result is False
        self._mock_conn.rollback.assert_called_once()

    def test_closes_resources(self):
        """关闭资源"""
        from models.quality_rule import QualityRuleDAO
        QualityRuleDAO.update(1, rule_name="规则B")
        self._mock_cursor.close.assert_called_once()
        self._mock_conn.close.assert_called_once()"""

NEW_UPDATE_SUCCESS = """    def test_success(self):
        """更新成功"""
        self._mock_cursor.rowcount = 1
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.update(
            rule_id=1, rule_name="规则B",
            product_types=[], condition_expr="",
            inspection_items=[]
        )
        assert result[0] is True
        assert "更新成功" in result[1]

    def test_exception_rollback(self):
        """异常回滚"""
        self._mock_cursor.execute.side_effect = Exception("DB error")
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.update(
            rule_id=1, rule_name="规则B",
            product_types=[], condition_expr="",
            inspection_items=[]
        )
        assert result[0] is False
        self._mock_conn.rollback.assert_called_once()

    def test_closes_resources(self):
        """关闭资源"""
        from models.quality_rule import QualityRuleDAO
        QualityRuleDAO.update(
            rule_id=1, rule_name="规则B",
            product_types=[], condition_expr="",
            inspection_items=[]
        )
        self._mock_cursor.close.assert_called_once()
        self._mock_conn.close.assert_called_once()"""

content = content.replace(OLD_UPDATE_SUCCESS, NEW_UPDATE_SUCCESS)

# 2. TestDelete - delete 返回 (True, msg)
OLD_DELETE_SUCCESS = """    def test_success(self):
        """删除成功"""
        self._mock_cursor.rowcount = 1
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.delete(1)
        assert result is True"""
NEW_DELETE_SUCCESS = """    def test_success(self):
        """删除成功"""
        self._mock_cursor.rowcount = 1
        from models.quality_rule import QualityRuleDAO
        result = QualityRuleDAO.delete(1)
        assert result[0] is True
        assert "删除成功" in result[1]"""

content = content.replace(OLD_DELETE_SUCCESS, NEW_DELETE_SUCCESS)

with open(FILE, "w", encoding="utf-8") as f:
    f.write(content)

print("✅ 修复完成")
