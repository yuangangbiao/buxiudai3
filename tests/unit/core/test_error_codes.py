# -*- coding: utf-8 -*-
r"""core/error_codes.py 的集成测试。

真源码行为(已读 d:\yuan\不锈钢网带跟单3.0\core\error_codes.py 验证):
- ErrorCode 类定义两次(第 10 行 class + 第 50 行 class 覆盖),最终以第 50 行为准
- ERRORS dict 第 163 行起为 StructuredErrorCode,第 532 行起混入 ErrorCode(不带 cause/solution)
- ERROR_CODES dict 第 783 行起为 dataclass ErrorCode(原 ERROR_CODES)
- 顶层别名(ERR_SYS_001 等)在第 1317 行起,ERRORS["ERR_SYS_001"] 绑定
- 查询函数 get_error/get_error_by_e_code/get_errors_by_domain/get_errors_by_severity_new/
  get_all_errors/get_error_count/get_errors_summary/get_error_info/get_all_error_codes/
  get_errors_by_severity/format_error_for_display/get_error_summary

按 F16 §1:不 mock 业务路径(直接 import 真模块),所有断言基于真实 dict 内容。
"""
import pytest

from core.error_codes import (
    ErrorCode, ErrorDomain, ErrorSeverity,
    StructuredErrorCode, ERRORS, ERROR_CODES,
    ERR_SYS_001, ERR_DB_001, ORDER_NOT_FOUND, AUTH_LOGIN_FAILED,
    get_error, get_error_by_e_code,
    get_errors_by_domain, get_errors_by_severity_new,
    get_all_errors, get_error_count, get_errors_summary,
    get_error_info, get_all_error_codes,
    get_errors_by_severity,
    format_error_for_display, get_error_summary,
)


def test_error_code_dataclass_attributes():
    r"""ErrorCode 是 @dataclass(第 770 行覆盖前面的 class),字段:code/name/message/cause/solution/severity。"""
    err = ErrorCode(
        code="ERR-TEST-001",
        name="测试错误",
        message="测试消息",
        cause="测试原因",
        solution="测试方案",
        severity="CRITICAL",
    )
    assert err.code == "ERR-TEST-001"
    assert err.name == "测试错误"
    assert err.message == "测试消息"
    assert err.cause == "测试原因"
    assert err.solution == "测试方案"
    assert err.severity == "CRITICAL"
    assert err.example is None
    assert err.related_codes is None


def test_error_code_dataclass_optional_fields():
    r"""ErrorCode example/related_codes 是 Optional,有默认值 None。"""
    err = ErrorCode(
        code="E001", name="n", message="m", cause="c", solution="s", severity="HIGH",
        example="示例", related_codes=["E002"],
    )
    assert err.example == "示例"
    assert err.related_codes == ["E002"]


def test_top_level_alias_uses_new_errorcode_class():
    r"""顶层别名(如 ORDER_NOT_FOUND)用的是第 50 行 ErrorCode class(覆盖前面 class),但实际
    字典在第 532 行用的是第 50 行后的版本。

    真源码(第 532 行起):ErrorCode(code, message, domain, severity, http_status=500)
    - 5 个位置参数(code, message, domain, severity),http_status 默认 500
    """
    assert ORDER_NOT_FOUND.code == "E1001"
    assert ORDER_NOT_FOUND.domain == ErrorDomain.ORDER
    assert ORDER_NOT_FOUND.http_status == 404


def test_error_domain_constants():
    r"""ErrorDomain 必须包含 6 个领域常量:ORDER/PRODUCTION/QUALITY/INVENTORY/SYSTEM/AUTH。"""
    assert ErrorDomain.ORDER == "order"
    assert ErrorDomain.PRODUCTION == "production"
    assert ErrorDomain.QUALITY == "quality"
    assert ErrorDomain.INVENTORY == "inventory"
    assert ErrorDomain.SYSTEM == "system"
    assert ErrorDomain.AUTH == "auth"


def test_error_severity_constants():
    r"""ErrorSeverity 必须包含 3 个级别常量:CRITICAL/ERROR/WARNING。"""
    assert ErrorSeverity.CRITICAL == "critical"
    assert ErrorSeverity.ERROR == "error"
    assert ErrorSeverity.WARNING == "warning"


def test_structured_error_code_extra_fields():
    r"""StructuredErrorCode 比 ErrorCode 多 cause/solution 字段。"""
    err = StructuredErrorCode(
        code="E9999", message="msg", domain="system", severity="error",
        http_status=500, cause="测试原因", solution="测试方案",
    )
    assert err.cause == "测试原因"
    assert err.solution == "测试方案"
    d = err.to_dict()
    assert d["cause"] == "测试原因"
    assert d["solution"] == "测试方案"


def test_errors_dict_contains_structured_error_codes():
    r"""ERRORS dict 必须含 ERR_SYS_001/ERR_DB_001 等键,值是 StructuredErrorCode 实例。"""
    assert "ERR_SYS_001" in ERRORS
    assert isinstance(ERRORS["ERR_SYS_001"], StructuredErrorCode)
    assert ERRORS["ERR_SYS_001"].code == "E0001"
    assert ERRORS["ERR_SYS_001"].domain == ErrorDomain.SYSTEM


def test_top_level_aliases_bind_to_errors_dict():
    r"""顶层别名 ERR_SYS_001 必须等同 ERRORS["ERR_SYS_001"]。"""
    assert ERR_SYS_001 is ERRORS["ERR_SYS_001"]
    assert ERR_DB_001 is ERRORS["ERR_DB_001"]
    assert ORDER_NOT_FOUND is ERRORS["ORDER_NOT_FOUND"]
    assert AUTH_LOGIN_FAILED is ERRORS["AUTH_LOGIN_FAILED"]


def test_get_error_returns_structured_error_code():
    r"""get_error(key) 必须返 ERRORS[key],不存在返 None。"""
    err = get_error("ERR_SYS_001")
    assert err is ERR_SYS_001
    assert get_error("NONEXISTENT_KEY") is None


def test_get_error_by_e_code_finds_correct_entry():
    r"""get_error_by_e_code('E0001') 必须返 ERR_SYS_001(E0001)。"""
    err = get_error_by_e_code("E0001")
    assert err is not None
    assert err.code == "E0001"
    assert err is ERR_SYS_001


def test_get_error_by_e_code_returns_none_for_unknown():
    r"""get_error_by_e_code 找不到时返 None(不抛异常)。"""
    assert get_error_by_e_code("E9999") is None


def test_get_errors_by_domain_returns_only_matching_domain():
    r"""get_errors_by_domain('order') 必须只返 domain='order' 的错误码。"""
    order_errors = get_errors_by_domain(ErrorDomain.ORDER)
    assert all(e.domain == ErrorDomain.ORDER for e in order_errors)
    assert len(order_errors) > 0


def test_get_errors_by_severity_new_returns_only_matching_severity():
    r"""get_errors_by_severity_new('critical') 必须只返 severity='critical' 的错误码。"""
    critical_errors = get_errors_by_severity_new(ErrorSeverity.CRITICAL)
    assert all(e.severity == ErrorSeverity.CRITICAL for e in critical_errors)
    assert len(critical_errors) > 0


def test_get_all_errors_returns_complete_dict():
    r"""get_all_errors() 必须返完整 ERRORS dict。"""
    assert get_all_errors() is ERRORS


def test_get_error_count_matches_dict_length():
    r"""get_error_count() 必须 == len(ERRORS)。"""
    assert get_error_count() == len(ERRORS)


def test_get_errors_summary_groups_by_domain_and_severity():
    r"""get_errors_summary() 必须返嵌套 dict{domain:{severity:count}}。"""
    summary = get_errors_summary()
    assert isinstance(summary, dict)
    for domain, sev_dict in summary.items():
        assert isinstance(sev_dict, dict)
        for sev, count in sev_dict.items():
            assert isinstance(count, int)
            assert count >= 1


def test_get_error_summary_count_matches_get_error_count():
    r"""get_errors_summary 各域各级别计数之和 == get_error_count。"""
    summary = get_errors_summary()
    total = sum(c for dom in summary.values() for c in dom.values())
    assert total == get_error_count()


def test_error_codes_dict_uses_dataclass_format():
    r"""ERROR_CODES(dict) 必须用 dataclass ErrorCode(有 name/cause/solution/example 字段)。"""
    assert "ERR-SYS-001" in ERROR_CODES
    err = ERROR_CODES["ERR-SYS-001"]
    assert err.code == "ERR-SYS-001"
    assert err.name == "Non-UTF-8编码错误"
    assert "UTF-8" in err.solution
    assert err.severity == "CRITICAL"


def test_get_error_info_returns_dataclass_error_code():
    r"""get_error_info(code) 必须返 ERROR_CODES[code],不存在返 None。"""
    err = get_error_info("ERR-SYS-001")
    assert err is not None
    assert err.code == "ERR-SYS-001"
    assert get_error_info("NONEXISTENT") is None


def test_get_all_error_codes_returns_all_keys():
    r"""get_all_error_codes() 必须返 ERROR_CODES 的所有 key 列表。"""
    codes = get_all_error_codes()
    assert "ERR-SYS-001" in codes
    assert "ERR-DB-001" in codes
    assert len(codes) == len(ERROR_CODES)


def test_get_errors_by_severity_filters_dataclass_dict():
    r"""get_errors_by_severity('CRITICAL') 必须返 ERROR_CODES 中 severity=='CRITICAL' 的列表。"""
    critical = get_errors_by_severity("CRITICAL")
    assert all(e.severity == "CRITICAL" for e in critical)
    assert len(critical) > 0


def test_format_error_for_display_contains_required_sections():
    r"""format_error_for_display 返字符串,必须含 错误编码/名称/严重程度/描述/原因/方案 6 段。"""
    text = format_error_for_display("ERR-SYS-001")
    assert "ERR-SYS-001" in text
    assert "Non-UTF-8编码错误" in text
    assert "CRITICAL" in text
    assert "【错误描述】" in text
    assert "【原因分析】" in text
    assert "【解决方案】" in text


def test_format_error_for_display_includes_example_when_present():
    r"""有 example 字段时,format_error_for_display 必须含【错误示例】段。"""
    text = format_error_for_display("ERR-SYS-001")
    assert "【错误示例】" in text


def test_format_error_for_display_unknown_code_falls_back():
    r"""未知 code 返 '未知错误编码: <code>'(不抛异常)。"""
    text = format_error_for_display("UNKNOWN-CODE")
    assert "未知错误编码: UNKNOWN-CODE" in text


def test_format_error_for_display_includes_original_error_when_unknown():
    r"""未知 code 且传 original_error 时,必须包含原始错误信息。"""
    text = format_error_for_display("UNKNOWN", original_error="底层报错 X")
    assert "底层报错 X" in text


def test_get_error_summary_groups_by_three_levels():
    r"""get_error_summary 返字符串,必须含 [CRITICAL]/[HIGH]/[MEDIUM] 3 段。"""
    text = get_error_summary()
    assert "[CRITICAL]" in text
    assert "[HIGH]" in text
    assert "[MEDIUM]" in text
    assert "ERR-SYS-001" in text
