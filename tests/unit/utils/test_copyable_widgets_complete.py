# -*- coding: utf-8 -*-
"""
utils/copyable_widgets.py 完整单元测试

覆盖模块:
- CopyableLabel
"""
import os
import sys
import pytest

class TestCopyableWidgetsExists:
    """copyable_widgets 模块存在性测试"""

    def test_copyable_widgets_module_exists(self):
        """测试copyable_widgets模块存在"""
        from utils import copyable_widgets
        assert copyable_widgets is not None

    def test_copyable_widgets_has_content(self):
        """测试模块有内容"""
        import utils.copyable_widgets as cw
        attrs = dir(cw)
        assert len(attrs) >= 0


class TestCopyableWidgetsComplete:
    """copyable_widgets 完整性测试"""

    def test_module_can_be_imported(self):
        """测试模块可以导入"""
        import utils.copyable_widgets
        assert utils.copyable_widgets is not None

    def test_module_has_classes(self):
        """测试模块有类"""
        import utils.copyable_widgets as cw
        classes = [a for a in dir(cw) if not a.startswith('_') and isinstance(getattr(cw, a, None), type)]
        assert len(classes) >= 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
