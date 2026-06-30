# -*- coding: utf-8 -*-
"""
core/error_codes.py 完整测试 - 覆盖 StructuredErrorCode 类方法、
ErrorCode dataclass 类方法、以及所有查询函数
"""
import sys, os
import pytest
from unittest.mock import patch, MagicMock


class TestStructuredErrorCodeMethods:
    """StructuredErrorCode 类方法测试 (L61-85)"""

    def test_str_representation(self):
        from core.error_codes import StructuredErrorCode, ErrorDomain, ErrorSeverity
        err = StructuredErrorCode(
            code="E0001",
            message="测试消息",
            domain=ErrorDomain.SYSTEM,
            severity=ErrorSeverity.ERROR,
            http_status=400,
        )
        s = str(err)
        assert "E0001" in s
        assert "测试消息" in s

    def test_repr_representation(self):
        from core.error_codes import StructuredErrorCode, ErrorDomain, ErrorSeverity
        err = StructuredErrorCode(
            code="E0001",
            message="测试消息",
            domain=ErrorDomain.SYSTEM,
            severity=ErrorSeverity.ERROR,
            http_status=400,
        )
        r = repr(err)
        assert "E0001" in r
        assert "system" in r

    def test_to_dict(self):
        from core.error_codes import StructuredErrorCode, ErrorDomain, ErrorSeverity
        err = StructuredErrorCode(
            code="E0001",
            message="测试消息",
            domain=ErrorDomain.SYSTEM,
            severity=ErrorSeverity.ERROR,
            http_status=400,
            cause="原因",
            solution="方案",
        )
        d = err.to_dict()
        assert d["code"] == "E0001"
        assert d["message"] == "测试消息"
        assert d["domain"] == ErrorDomain.SYSTEM
        assert d["severity"] == ErrorSeverity.ERROR
        assert d["http_status"] == 400
        assert d["cause"] == "原因"
        assert d["solution"] == "方案"


class TestLightweightErrorCode:
    """ErrorCode 轻量级类方法测试 (L50-85)

    该轻量级 ErrorCode 类位于 core/error_codes.py 第50行，
    被第771行的 dataclass ErrorCode 同名覆盖，无法通过正常 import 访问。
    通过 gc.get_objects() 查找带 to_dict 的 ErrorCode 类来获取引用。
    """

    @staticmethod
    def _get_lightweight_errorcode():
        import gc
        for obj in gc.get_objects():
            if isinstance(obj, type) and obj.__name__ == 'ErrorCode':
                if 'to_dict' in obj.__dict__:
                    return obj
        raise RuntimeError("无法找到轻量级 ErrorCode 类")

    def test_lightweight_str(self):
        ec_cls = self._get_lightweight_errorcode()
        err = ec_cls(code="E1001", message="订单不存在", domain="order", severity="error", http_status=404)
        assert str(err) == "[E1001] 订单不存在"

    def test_lightweight_repr(self):
        ec_cls = self._get_lightweight_errorcode()
        err = ec_cls(code="E1001", message="订单不存在", domain="order", severity="error", http_status=404)
        r = repr(err)
        assert "E1001" in r
        assert "order" in r
        assert "error" in r
        assert "404" in r

    def test_lightweight_to_dict(self):
        ec_cls = self._get_lightweight_errorcode()
        err = ec_cls(code="E1001", message="订单不存在", domain="order", severity="error", http_status=404)
        d = err.to_dict()
        assert d["code"] == "E1001"
        assert d["message"] == "订单不存在"
        assert d["domain"] == "order"
        assert d["severity"] == "error"
        assert d["http_status"] == 404
        assert len(d) == 5


class TestErrorCodeDataclassMethods:
    """ErrorCode dataclass 类方法测试 (L770+)"""

    def test_error_code_str(self):
        from core.error_codes import ErrorCode
        err = ErrorCode(
            code="ERR-SYS-001",
            name="Non-UTF-8",
            message="非UTF-8",
            cause="编码问题",
            solution="转UTF-8",
            severity="CRITICAL",
        )
        s = str(err)
        assert "ERR-SYS-001" in s
        assert "非UTF-8" in s

    def test_error_code_repr(self):
        from core.error_codes import ErrorCode
        err = ErrorCode(
            code="ERR-SYS-001",
            name="Non-UTF-8",
            message="非UTF-8",
            cause="编码问题",
            solution="转UTF-8",
            severity="CRITICAL",
        )
        r = repr(err)
        assert "ERR-SYS-001" in r


class TestStructuredErrorLookupFunctions:
    """结构化错误码查询函数测试 (L724-763)"""

    def test_get_error_found(self):
        from core.error_codes import get_error
        err = get_error("ERR_SYS_001")
        assert err is not None
        assert err.code == "E0001"

    def test_get_error_not_found(self):
        from core.error_codes import get_error
        err = get_error("NOT_EXIST")
        assert err is None

    def test_get_error_by_e_code_found(self):
        from core.error_codes import get_error_by_e_code
        err = get_error_by_e_code("E0001")
        assert err is not None
        assert err.code == "E0001"

    def test_get_error_by_e_code_not_found(self):
        from core.error_codes import get_error_by_e_code
        err = get_error_by_e_code("E9999")
        assert err is None

    def test_get_errors_by_domain(self):
        from core.error_codes import get_errors_by_domain
        errors = get_errors_by_domain("system")
        assert isinstance(errors, list)
        # 所有 system 领域的错误
        for e in errors:
            assert e.domain == "system"

    def test_get_errors_by_domain_not_found(self):
        from core.error_codes import get_errors_by_domain
        errors = get_errors_by_domain("nonexistent_domain")
        assert isinstance(errors, list)

    def test_get_errors_by_severity_new(self):
        from core.error_codes import get_errors_by_severity_new
        errors = get_errors_by_severity_new("critical")
        assert isinstance(errors, list)
        for e in errors:
            assert e.severity == "critical"

    def test_get_errors_by_severity_new_not_found(self):
        from core.error_codes import get_errors_by_severity_new
        errors = get_errors_by_severity_new("nonexistent")
        assert isinstance(errors, list)

    def test_get_all_errors(self):
        from core.error_codes import get_all_errors
        all_errors = get_all_errors()
        assert isinstance(all_errors, dict)
        assert len(all_errors) > 0

    def test_get_error_count(self):
        from core.error_codes import get_error_count, get_all_errors
        count = get_error_count()
        all_errors = get_all_errors()
        assert count == len(all_errors)
        assert count > 0

    def test_get_errors_summary(self):
        from core.error_codes import get_errors_summary
        summary = get_errors_summary()
        assert isinstance(summary, dict)


class TestOriginalErrorLookupFunctions:
    """原有 ERROR_CODES 查询函数测试 (L1225-1308)"""

    def test_get_error_info_found(self):
        from core.error_codes import get_error_info
        info = get_error_info("ERR-SYS-001")
        assert info is not None
        assert info.code == "ERR-SYS-001"

    def test_get_error_info_not_found(self):
        from core.error_codes import get_error_info
        info = get_error_info("NOT-EXIST")
        assert info is None

    def test_get_all_error_codes(self):
        from core.error_codes import get_all_error_codes
        codes = get_all_error_codes()
        assert isinstance(codes, list)
        assert len(codes) > 0
        assert "ERR-SYS-001" in codes

    def test_get_errors_by_severity(self):
        from core.error_codes import get_errors_by_severity
        errors = get_errors_by_severity("CRITICAL")
        assert isinstance(errors, list)
        for e in errors:
            assert e.severity == "CRITICAL"

    def test_get_errors_by_severity_not_found(self):
        from core.error_codes import get_errors_by_severity
        errors = get_errors_by_severity("NOTEXIST")
        assert isinstance(errors, list)

    def test_format_error_for_display_found(self):
        from core.error_codes import format_error_for_display
        result = format_error_for_display("ERR-SYS-001", "some error")
        assert "ERR-SYS-001" in result
        assert "严重程度" in result

    def test_format_error_for_display_not_found(self):
        from core.error_codes import format_error_for_display
        result = format_error_for_display("NOT-EXIST", "raw error")
        assert "未知错误编码" in result
        assert "raw error" in result

    def test_format_error_for_display_without_original(self):
        from core.error_codes import format_error_for_display
        result = format_error_for_display("ERR-SYS-001")
        assert "ERR-SYS-001" in result

    def test_get_error_summary(self):
        from core.error_codes import get_error_summary
        summary = get_error_summary()
        assert isinstance(summary, str)
        assert "错误编码体系摘要" in summary


class TestErrorCodeConstants:
    """错误码常量测试"""

    def test_error_domain_constants(self):
        from core.error_codes import ErrorDomain
        assert ErrorDomain.ORDER == "order"
        assert ErrorDomain.PRODUCTION == "production"
        assert ErrorDomain.QUALITY == "quality"
        assert ErrorDomain.SYSTEM == "system"
        assert ErrorDomain.AUTH == "auth"

    def test_error_severity_constants(self):
        from core.error_codes import ErrorSeverity
        assert ErrorSeverity.CRITICAL == "critical"
        assert ErrorSeverity.ERROR == "error"
        assert ErrorSeverity.WARNING == "warning"

    def test_error_codes_dict_has_required_keys(self):
        from core.error_codes import ERRORS
        required_keys = ["ERR_SYS_001", "ERR_SYS_002", "ERR_SYS_003"]
        for key in required_keys:
            assert key in ERRORS
            assert ERRORS[key].code is not None
            assert ERRORS[key].message is not None
