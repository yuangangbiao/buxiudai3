# -*- coding: utf-8 -*-
"""
批量修复 test_quality_rule.py 中缺失 _setup_mock 的测试类

策略：
1. 为每个缺 _setup_mock 的类添加 _setup_mock fixture
2. 将 cursor 参数替换为 self._mock_cursor
3. 将 mock_conn 参数替换为 self._mock_conn
"""
import re

FILE = r"d:\yuan\不锈钢网带跟单3.0\tests\unit\models\test_quality_rule.py"

SETUP_MOCK = '''
    @pytest.fixture(autouse=True)
    def _setup_mock(self, monkeypatch):
        self._mock_conn = MagicMock()
        self._mock_cursor = MagicMock()
        self._mock_conn.cursor.return_value = self._mock_cursor

        def fake_get_connection(*args, **kwargs):
            return self._mock_conn

        monkeypatch.setattr("models.quality_rule.get_connection", fake_get_connection)
        monkeypatch.setattr("models.database.get_connection", fake_get_connection)
        monkeypatch.setattr("core.db.get_connection", fake_get_connection)
        monkeypatch.setattr("utils.op_logger.log", lambda *a, **kw: None)
        monkeypatch.setattr("utils.op_logger.log_error", lambda *a, **kw: None)

'''

CLASSES_TO_FIX = [
    "TestGetRulesByProcess",
    "TestCreate",
    "TestUpdate",
    "TestDelete",
    "TestGetRuleItems",
    "TestSaveRuleItems",
    "TestAddRuleItem",
    "TestGetMatchingRules",
    "TestEvaluateQualityRules",
    "TestInitDefaultRules",
]


def fix_class(content, class_name):
    """为一个类添加 _setup_mock 并替换 fixture 参数"""
    # 找到类的起始
    class_pattern = rf"(# ===================== {re.escape(class_name)} =====================\n\nclass {re.escape(class_name)}:)"
    match = re.search(class_pattern, content)
    if not match:
        print(f"  ⊘ 未找到: {class_name}")
        return content, False

    insert_pos = match.end()
    content = content[:insert_pos] + SETUP_MOCK + content[insert_pos:]

    # 替换函数参数中的 cursor → self._mock_cursor
    content = re.sub(
        rf"(def (test_\w+)\(self, cursor(,\s*mock_conn)?\))",
        lambda m: f"def {m.group(2)}(self{m.group(3).replace('cursor', 'self._mock_cursor').replace('mock_conn', 'self._mock_conn') if m.group(3) else ''})",
        content
    )
    # 更简单的替换：在类内的所有函数签名中，将 cursor 参数替换为 self._mock_cursor
    # 找到类定义的范围
    class_start = content.index(f"class {class_name}:")
    # 找到下一个 class 或文件结束
    remaining = content[class_start + len(f"class {class_name}:"):]
    next_class = remaining.find("\nclass Test")
    if next_class == -1:
        class_end = len(content)
    else:
        class_end = class_start + len(f"class {class_name}:") + next_class

    class_content = content[class_start:class_end]

    # 在类内替换 self, cursor → self, self._mock_cursor 和 self, mock_conn → self, self._mock_conn
    def replace_cursor_param(m):
        indent = m.group(1)
        func_name = m.group(2)
        params = m.group(3)
        params = params.replace("cursor, ", "self._mock_cursor, ")
        params = params.replace("cursor", "self._mock_cursor")
        params = params.replace("mock_conn, ", "self._mock_conn, ")
        params = params.replace("mock_conn", "self._mock_conn")
        return f"{indent}def {func_name}(self{params})"

    fixed_class = re.sub(
        r"(\n    )(def (test_\w+)\(self,?\s*)(cursor|self\._mock_cursor)(,?\s*)(mock_conn|self\._mock_conn)?(\))",
        lambda m: f"{m.group(1)}{m.group(3)}(self{',' if m.group(5).strip() else ''}{m.group(4).replace('cursor','self._mock_cursor')}{',' if m.group(6) and m.group(6).strip() else ''}{m.group(6).replace('mock_conn','self._mock_conn') if m.group(6) else ''})",
        class_content
    )

    content = content[:class_start] + fixed_class + content[class_end:]
    print(f"  ✓ 修复: {class_name}")
    return content, True


def main():
    with open(FILE, "r", encoding="utf-8") as f:
        content = f.read()

    for class_name in CLASSES_TO_FIX:
        content, ok = fix_class(content, class_name)

    with open(FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print("\n✅ 全部修复完成！")


if __name__ == "__main__":
    main()
