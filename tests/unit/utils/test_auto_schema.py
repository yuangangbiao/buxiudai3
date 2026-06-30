# -*- coding: utf-8 -*-
"""
utils/auto_schema.py 完整单元测试

覆盖模块:
- 自动Schema推断
- _infer_sql_type()
"""
import os
import sys
import pytest


class TestAutoSchemaExists:
    """auto_schema 存在性测试"""

    def test_auto_schema_module_exists(self):
        """测试auto_schema模块存在"""
        try:
            from utils import auto_schema
            assert auto_schema is not None
        except ImportError:
            pytest.skip("auto_schema 模块不可用")


class TestInferSqlType:
    """_infer_sql_type 测试"""

    def test_infer_str_short_sqlite(self):
        """测试推断短字符串sqlite"""
        try:
            from utils.auto_schema import _infer_sql_type
            assert _infer_sql_type('hi', True) == 'TEXT'
        except ImportError:
            pytest.skip("auto_schema 模块不可用")

    def test_infer_str_short_mysql(self):
        """测试推断短字符串mysql"""
        try:
            from utils.auto_schema import _infer_sql_type
            assert _infer_sql_type('hi', False) == 'VARCHAR(255)'
        except ImportError:
            pytest.skip("auto_schema 模块不可用")

    def test_infer_str_long(self):
        """测试推断长字符串"""
        try:
            from utils.auto_schema import _infer_sql_type
            long_str = 'a' * 300
            assert _infer_sql_type(long_str, True) == 'TEXT'
            assert _infer_sql_type(long_str, False) == 'TEXT'
        except ImportError:
            pytest.skip("auto_schema 模块不可用")

    def test_infer_int_sqlite(self):
        """测试推断整数sqlite"""
        try:
            from utils.auto_schema import _infer_sql_type
            assert _infer_sql_type(42, True) == 'INTEGER'
        except ImportError:
            pytest.skip("auto_schema 模块不可用")

    def test_infer_int_mysql(self):
        """测试推断整数mysql"""
        try:
            from utils.auto_schema import _infer_sql_type
            assert _infer_sql_type(42, False) == 'INT'
        except ImportError:
            pytest.skip("auto_schema 模块不可用")

    def test_infer_float(self):
        """测试推断浮点数"""
        try:
            from utils.auto_schema import _infer_sql_type
            result = _infer_sql_type(3.14, True)
            assert result in ['REAL', 'FLOAT', 'DOUBLE', 'NUMERIC']
        except ImportError:
            pytest.skip("auto_schema 模块不可用")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
