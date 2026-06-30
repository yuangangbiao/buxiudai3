# -*- coding: utf-8 -*-
"""
P0-T5 + P0-T8 单元测试 - 模板数量一致性 + uuid 替换

测试范围:
- P0-T5: 微信消息模板数量统一为 54（原 33/50/54 矛盾）
- P0-T8: test_business_correctness.py 12 处 uuid.uuid4() 替换为 _next_test_id()
"""
import os
import sys
import re
import ast
import importlib
import pytest

# 项目根目录加入 sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'mobile_api_ai'))


class TestP0T5TemplateCountConsistency:
    """P0-T5: 微信消息模板数量三处矛盾修复"""

    def test_template_engine_test_asserts_54(self):
        """test_template_engine.py 断言模板数 = 54"""
        test_path = os.path.join(BASE_DIR, 'tests', 'unit', 'test_template_engine.py')
        with open(test_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert 'assert len(MESSAGE_TEMPLATES_DEFAULT) == 54' in source, \
            "test_template_engine.py 应断言模板数 = 54"

    def test_template_engine_test_method_naming(self):
        """test_template_engine.py 方法名应统一（不再叫 50_templates）"""
        test_path = os.path.join(BASE_DIR, 'tests', 'unit', 'test_template_engine.py')
        with open(test_path, 'r', encoding='utf-8') as f:
            source = f.read()
        # 不应该再有 test_all_50_templates_exist
        assert 'test_all_50_templates_exist' not in source
        # 应该有 test_all_54_templates_exist
        assert 'test_all_54_templates_exist' in source

    def test_architecture_doc_consistent_54(self):
        """ARCHITECTURE_v3.6.md 模板数量描述统一为 54"""
        doc_path = os.path.join(BASE_DIR, 'mobile_api_ai', 'docs', 'ARCHITECTURE_v3.6.md')
        with open(doc_path, 'r', encoding='utf-8') as f:
            source = f.read()
        # 验证提到 54
        assert '54 个模板' in source or '54 个' in source
        # 不应再有 53 个模板
        assert '53 个模板' not in source
        # 不应再有 50 个模板的描述（与 54 不一致）
        # 注意：50 可能出现在 "50%" 等场景，所以只检查 "50 个模板"
        assert '50 个模板' not in source, "ARCHITECTURE_v3.6.md 不应再含 '50 个模板'"


class TestP0T8UUIDReplaced:
    """P0-T8: uuid.uuid4() 替换为 _next_test_id()"""

    def test_business_correctness_no_uuid4(self):
        """test_business_correctness.py 不再使用 uuid.uuid4()"""
        test_path = os.path.join(BASE_DIR, 'tests', 'test_business_correctness.py')
        with open(test_path, 'r', encoding='utf-8') as f:
            source = f.read()

        # 检查实际代码（排除 docstring/注释）
        tree = ast.parse(source)
        uuid_used_in_code = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # 检查 func 是否是 uuid.uuid4
                if isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name) and node.func.value.id == 'uuid' and node.func.attr == 'uuid4':
                        uuid_used_in_code = True
                        break

        assert not uuid_used_in_code, "test_business_correctness.py 仍调用 uuid.uuid4()"
        # 也不应该再 import uuid
        uuid_imported = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == 'uuid':
                        uuid_imported = True
        assert not uuid_imported, "test_business_correctness.py 仍 import uuid"

    def test_business_correctness_uses_next_test_id(self):
        """test_business_correctness.py 使用 _next_test_id()"""
        test_path = os.path.join(BASE_DIR, 'tests', 'test_business_correctness.py')
        with open(test_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert 'def _next_test_id' in source, \
            "test_business_correctness.py 应定义 _next_test_id()"
        assert '_next_test_id()' in source, \
            "test_business_correctness.py 应使用 _next_test_id()"
        assert '_next_test_id(32)' in source, \
            "test_business_correctness.py 应使用 _next_test_id(32) 替代 str(uuid.uuid4())"

    def test_business_correctness_count(self):
        """test_business_correctness.py _next_test_id 调用次数 = 12（替代 12 处 uuid）"""
        test_path = os.path.join(BASE_DIR, 'tests', 'test_business_correctness.py')
        with open(test_path, 'r', encoding='utf-8') as f:
            source = f.read()
        # 计数 _next_test_id() 调用
        count = source.count('_next_test_id()') + source.count('_next_test_id(32)')
        assert count == 12, f"应该有 12 处 _next_test_id() 调用，实际 {count} 处"

    def test_business_correctness_syntax(self):
        """test_business_correctness.py Python 语法正确"""
        test_path = os.path.join(BASE_DIR, 'tests', 'test_business_correctness.py')
        with open(test_path, 'r', encoding='utf-8') as f:
            source = f.read()
        try:
            ast.parse(source)
        except SyntaxError as e:
            pytest.fail(f"test_business_correctness.py 语法错误: {e}")


class TestP0T8DeterministicIDs:
    """P0-T8 进阶验证：确定性 ID 可复现性"""

    def test_next_test_id_deterministic(self):
        """_next_test_id 连续调用产生确定性 ID"""
        # 重新加载模块
        import importlib
        if 'test_business_correctness' in sys.modules:
            importlib.reload(sys.modules['test_business_correctness'])
        from test_business_correctness import _next_test_id

        # 第一次调用应该返回 '000001'
        id1 = _next_test_id()
        assert id1 == '000001'

        # 第二次调用应该返回 '000002'
        id2 = _next_test_id()
        assert id2 == '000002'

    def test_next_test_id_custom_length(self):
        """_next_test_id 支持自定义长度"""
        if 'test_business_correctness' in sys.modules:
            importlib.reload(sys.modules['test_business_correctness'])
        from test_business_correctness import _next_test_id

        # 32 长度（替代 str(uuid.uuid4())）
        id_32 = _next_test_id(32)
        assert len(id_32) == 32
        assert id_32.isdigit()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
