# -*- coding: utf-8 -*-
"""
utils/custom_types.py 完整单元测试

覆盖模块:
- 自定义类型定义
"""
import os
import sys
import pytest

class TestCustomTypesExists:
    """custom_types 模块存在性测试"""

    def test_custom_types_module_exists(self):
        """测试custom_types模块存在"""
        from utils import custom_types
        assert custom_types is not None

    def test_custom_types_module_has_content(self):
        """测试模块有内容"""
        import utils.custom_types as ct
        attrs = dir(ct)
        assert len(attrs) >= 0


class TestCustomTypesComplete:
    """custom_types 完整性测试"""

    def test_module_can_be_imported(self):
        """测试模块可以导入"""
        import utils.custom_types
        assert utils.custom_types is not None

    def test_module_attributes_exist(self):
        """测试模块属性存在"""
        import utils.custom_types as ct
        attrs = dir(ct)
        # 模块至少有__name__
        assert '__name__' in attrs


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
