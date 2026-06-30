# -*- coding: utf-8 -*-
"""
core/error_codes_structured.py 完整单元测试

覆盖模块:
- ErrorCode
- ErrorDomain
- ErrorSeverity
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest


class TestErrorCodeExists:
    """ErrorCode 存在性测试"""

    def test_error_codes_structured_module_exists(self):
        """测试error_codes_structured模块存在"""
        from core import error_codes_structured
        assert error_codes_structured is not None

    def test_error_code_class_exists(self):
        """测试ErrorCode类存在"""
        from core.error_codes_structured import ErrorCode
        assert ErrorCode is not None

    def test_error_domain_class_exists(self):
        """测试ErrorDomain类存在"""
        from core.error_codes_structured import ErrorDomain
        assert ErrorDomain is not None

    def test_error_severity_class_exists(self):
        """测试ErrorSeverity类存在"""
        from core.error_codes_structured import ErrorSeverity
        assert ErrorSeverity is not None


class TestErrorCode:
    """ErrorCode 测试"""

    def test_init(self):
        """测试初始化"""
        from core.error_codes_structured import ErrorCode
        ec = ErrorCode("E1001", "测试错误", "system", "error")
        assert ec.code == "E1001"
        assert ec.message == "测试错误"
        assert ec.domain == "system"
        assert ec.severity == "error"
        assert ec.http_status == 500

    def test_init_with_http_status(self):
        """测试带http_status初始化"""
        from core.error_codes_structured import ErrorCode
        ec = ErrorCode("E2001", "未授权", "auth", "error", http_status=401)
        assert ec.http_status == 401

    def test_repr(self):
        """测试__repr__"""
        from core.error_codes_structured import ErrorCode
        ec = ErrorCode("E1001", "测试", "system", "error")
        repr_str = repr(ec)
        assert "E1001" in repr_str
        assert "测试" in repr_str

    def test_eq(self):
        """测试相等性"""
        from core.error_codes_structured import ErrorCode
        ec1 = ErrorCode("E1001", "测试", "system", "error")
        ec2 = ErrorCode("E1001", "不同消息", "auth", "warning")
        ec3 = ErrorCode("E1002", "测试", "system", "error")

        assert ec1 == ec2  # 相等基于code
        assert ec1 != ec3  # 不同code不相等
        assert ec1 != "string"  # 与非ErrorCode不相等


class TestErrorDomain:
    """ErrorDomain 测试"""

    def test_domain_constants(self):
        """测试域常量"""
        from core.error_codes_structured import ErrorDomain
        assert ErrorDomain.ORDER == "order"
        assert ErrorDomain.PRODUCTION == "production"
        assert ErrorDomain.QUALITY == "quality"
        assert ErrorDomain.INVENTORY == "inventory"
        assert ErrorDomain.SYSTEM == "system"
        assert ErrorDomain.AUTH == "auth"


class TestErrorSeverity:
    """ErrorSeverity 测试"""

    def test_severity_constants(self):
        """测试严重程度常量"""
        from core.error_codes_structured import ErrorSeverity
        assert ErrorSeverity.CRITICAL == "critical"
        assert ErrorSeverity.ERROR == "error"
        assert ErrorSeverity.WARNING == "warning"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
