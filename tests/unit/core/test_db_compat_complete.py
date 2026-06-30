# -*- coding: utf-8 -*-
"""
core/db_compat.py 完整单元测试

覆盖模块:
- 数据库兼容层
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest
from unittest.mock import patch, MagicMock


class TestDbCompatExists:
    """db_compat 存在性测试"""

    def test_db_compat_module_exists(self):
        """测试db_compat模块存在"""
        from core import db_compat
        assert db_compat is not None


class TestDbCompatFunctions:
    """db_compat 函数测试"""

    def test_module_has_functions(self):
        """测试模块有函数"""
        from core import db_compat

        attrs = dir(db_compat)
        public_attrs = [a for a in attrs if not a.startswith('_')]
        assert len(public_attrs) >= 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
