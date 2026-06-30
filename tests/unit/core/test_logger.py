# -*- coding: utf-8 -*-
r"""core/logger.py 的集成测试。

真源码行为(已读 d:\yuan\不锈钢网带跟单3.0\core\logger.py 验证):
- LogManager 单例(__new__ + _initialized flag),__init__ 用 _initialized 防止重复初始化
- _create_logger(name, level=INFO) 加 StreamHandler + RotatingFileHandler(10MB, 5 backups)
  - 已存在 handler 的 logger 直接返,不重复加
- get_logger(name): 缓存到 _loggers
- StructuredLogger 包装 logging.Logger:_log 用 json.dumps 序列化 extra 字典
  - 5 个方法: info/warning/error/debug/critical
  - exception() 自动附 traceback
- get_request_id(): Flask has_request_context() 优先取 X-Request-ID,否则 uuid4()[:8]
- log_with_trace(msg, level='info', **kwargs): 自动加 [trace_id] 前缀

按 F16 §1:不 mock 业务路径,patch flask.has_request_context 隔离请求上下文。
"""
import logging
import re
from unittest.mock import MagicMock, patch

import pytest

from core.logger import (
    LogManager, log_manager,
    get_logger, get_structured_logger,
    get_request_id, log_with_trace,
    StructuredLogger,
)


def test_log_manager_is_singleton():
    r"""LogManager 多次 __new__ 必须返同一实例。"""
    a = LogManager()
    b = LogManager()
    assert a is b


def test_log_manager_init_only_once():
    r"""LogManager __init__ 用 _initialized flag 防重复初始化。

    测试隔离:用 monkeypatch 重置 _instance/_initialized 后创建新实例,验证
    __init__ 不会重复初始化。但是需要在测试结束时恢复原状态,避免污染后续测试。
    """
    import pytest as _pytest
    original_instance = LogManager._instance
    original_initialized = LogManager._initialized

    try:
        LogManager._instance = None
        LogManager._initialized = False
        lm = LogManager()
        assert lm._initialized is True
        initial_loggers = dict(lm._loggers)
        lm.__init__()
        assert lm._loggers == initial_loggers
    finally:
        LogManager._instance = original_instance
        LogManager._initialized = original_initialized


def test_log_manager_creates_log_dir(monkeypatch):
    r"""LogManager __init__ 调 LOG_DIR.mkdir(parents=True, exist_ok=True)。

    测试隔离:重置 _instance/_initialized 创建新实例,最后恢复原状态。
    """
    original_instance = LogManager._instance
    original_initialized = LogManager._initialized

    try:
        LogManager._instance = None
        LogManager._initialized = False
        from core import logger as lgr
        fake_dir = MagicMock()
        monkeypatch.setattr(lgr, "LOG_DIR", fake_dir)
        lm = LogManager()
        fake_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        _ = lm
    finally:
        LogManager._instance = original_instance
        LogManager._initialized = original_initialized


def test_get_logger_returns_logger_instance():
    r"""get_logger(name) 返 logging.Logger 实例。"""
    logger = get_logger("test_module_1")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_module_1"


def test_get_logger_caches_in_log_manager():
    r"""get_logger 同一 name 第二次调用从缓存返(不重新创建)。"""
    lm = LogManager()
    initial_count = len(lm._loggers)
    get_logger("test_module_cached")
    assert "test_module_cached" in lm._loggers
    get_logger("test_module_cached")
    assert len(lm._loggers) == initial_count + 1


def test_create_logger_does_not_double_add_handlers():
    r"""_create_logger 已有 handlers 的 logger 直接返,不重复添加。"""
    lm = LogManager()
    logger = lm._create_logger("test_double_handler")
    initial_handler_count = len(logger.handlers)
    same = lm._create_logger("test_double_handler")
    assert same is logger
    assert len(logger.handlers) == initial_handler_count


def test_structured_logger_info_appends_json():
    r"""StructuredLogger.info(msg, **extra) 必须把 extra 序列化为 JSON 附加到 msg。"""
    base = logging.getLogger("test_structured_info")
    slog = StructuredLogger(base)
    with patch.object(base, "log") as mock_log:
        slog.info("订单创建", order_no="GO-001", operator="张三")
        mock_log.assert_called_once()
        level, formatted_msg = mock_log.call_args.args
        assert level == logging.INFO
        assert formatted_msg.startswith("订单创建 | ")
        assert '"order_no": "GO-001"' in formatted_msg
        assert '"operator": "张三"' in formatted_msg
        assert '"timestamp"' in formatted_msg


def test_structured_logger_warning_uses_warning_level():
    r"""StructuredLogger.warning 必须用 WARNING level。"""
    base = logging.getLogger("test_structured_warning")
    slog = StructuredLogger(base)
    with patch.object(base, "log") as mock_log:
        slog.warning("库存预警", material="304不锈钢")
        mock_log.assert_called_once()
        level = mock_log.call_args.args[0]
        assert level == logging.WARNING


def test_structured_logger_error_uses_error_level():
    r"""StructuredLogger.error 必须用 ERROR level。"""
    base = logging.getLogger("test_structured_error")
    slog = StructuredLogger(base)
    with patch.object(base, "log") as mock_log:
        slog.error("操作失败", error="timeout")
        mock_log.assert_called_once()
        level = mock_log.call_args.args[0]
        assert level == logging.ERROR


def test_structured_logger_debug_uses_debug_level():
    r"""StructuredLogger.debug 必须用 DEBUG level。"""
    base = logging.getLogger("test_structured_debug")
    slog = StructuredLogger(base)
    with patch.object(base, "log") as mock_log:
        slog.debug("调试信息")
        mock_log.assert_called_once()
        level = mock_log.call_args.args[0]
        assert level == logging.DEBUG


def test_structured_logger_critical_uses_critical_level():
    r"""StructuredLogger.critical 必须用 CRITICAL level。"""
    base = logging.getLogger("test_structured_critical")
    slog = StructuredLogger(base)
    with patch.object(base, "log") as mock_log:
        slog.critical("严重错误")
        mock_log.assert_called_once()
        level = mock_log.call_args.args[0]
        assert level == logging.CRITICAL


def test_structured_logger_exception_uses_exception_method():
    r"""StructuredLogger.exception 必须用 logger.exception()(自动附 traceback)。"""
    base = logging.getLogger("test_structured_exception")
    slog = StructuredLogger(base)
    with patch.object(base, "exception") as mock_exc:
        slog.exception("异常日志", order_no="GO-001")
        mock_exc.assert_called_once()
        msg = mock_exc.call_args.args[0]
        assert msg.startswith("异常日志 | ")
        assert '"order_no": "GO-001"' in msg


def test_structured_logger_extra_default_timestamp():
    r"""StructuredLogger 自动给 extra 加 timestamp 字段(源码第 120 行)。"""
    base = logging.getLogger("test_structured_ts")
    slog = StructuredLogger(base)
    with patch.object(base, "log") as mock_log:
        slog.info("test")
        msg = mock_log.call_args.args[1]
        assert '"timestamp"' in msg


def test_structured_logger_extra_custom_not_overridden():
    r"""StructuredLogger 不覆盖用户传的 timestamp(用 setdefault)。"""
    base = logging.getLogger("test_structured_ts2")
    slog = StructuredLogger(base)
    with patch.object(base, "log") as mock_log:
        slog.info("test", timestamp="custom-fixed-ts")
        msg = mock_log.call_args.args[1]
        assert '"custom-fixed-ts"' in msg


def test_get_structured_logger_returns_wrapped():
    r"""get_structured_logger(name) 返 StructuredLogger 实例。"""
    slog = get_structured_logger("test_get_structured")
    assert isinstance(slog, StructuredLogger)


def test_get_request_id_outside_flask_context():
    r"""非 Flask 请求上下文时,get_request_id 返 8 位 uuid 字符串。"""
    rid = get_request_id()
    assert isinstance(rid, str)
    assert len(rid) == 8
    assert re.match(r"^[0-9a-f]{8}$", rid)


def test_get_request_id_inside_flask_context_with_header(monkeypatch):
    r"""Flask 请求上下文且有 X-Request-ID 头时,返头部值。"""
    fake_flask = MagicMock()
    fake_flask.has_request_context.return_value = True
    fake_request = MagicMock()
    fake_request.headers.get.return_value = "client-rid-12345"
    fake_flask.request = fake_request

    import sys
    monkeypatch.setitem(sys.modules, "flask", fake_flask)
    rid = get_request_id()
    assert rid == "client-rid-12345"


def test_get_request_id_inside_flask_context_no_header(monkeypatch):
    r"""Flask 请求上下文但无 X-Request-ID 时,降级到 8 位 uuid。"""
    fake_flask = MagicMock()
    fake_flask.has_request_context.return_value = True
    fake_request = MagicMock()
    fake_request.headers.get.return_value = ""
    fake_flask.request = fake_request

    import sys
    monkeypatch.setitem(sys.modules, "flask", fake_flask)
    rid = get_request_id()
    assert len(rid) == 8
    assert re.match(r"^[0-9a-f]{8}$", rid)


def test_get_request_id_handles_flask_import_error(monkeypatch):
    r"""Flask 导入失败时降级到 8 位 uuid(源码第 178-179 行 except)。"""
    import builtins
    real_import = builtins.__import__
    def fake_import(name, *args, **kwargs):
        if name == "flask":
            raise ImportError("flask not installed")
        return real_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", fake_import)
    rid = get_request_id()
    assert len(rid) == 8


def test_log_with_trace_adds_trace_id_prefix(monkeypatch):
    r"""log_with_trace(msg) 必须前缀 [trace_id]。"""
    import sys
    fake_flask = MagicMock()
    fake_flask.has_request_context.return_value = False
    monkeypatch.setitem(sys.modules, "flask", fake_flask)
    with patch("core.logger.logging.getLogger") as mock_get:
        mock_logger = MagicMock()
        mock_get.return_value = mock_logger
        log_with_trace("订单创建成功", level="info", order_no="GO-001")
        mock_logger.info.assert_called_once()
        msg = mock_logger.info.call_args.args[0]
        assert msg.startswith("[")
        assert msg.endswith("] 订单创建成功")
        assert mock_logger.info.call_args.kwargs.get("order_no") == "GO-001"


def test_log_with_trace_supports_error_level(monkeypatch):
    r"""log_with_trace level='error' 必须调 logger.error()。"""
    import sys
    fake_flask = MagicMock()
    fake_flask.has_request_context.return_value = False
    monkeypatch.setitem(sys.modules, "flask", fake_flask)
    with patch("core.logger.logging.getLogger") as mock_get:
        mock_logger = MagicMock()
        mock_get.return_value = mock_logger
        log_with_trace("同步失败", level="error")
        mock_logger.error.assert_called_once()


def test_log_with_trace_default_level_is_info(monkeypatch):
    r"""log_with_trace 不传 level 时默认 info。"""
    import sys
    fake_flask = MagicMock()
    fake_flask.has_request_context.return_value = False
    monkeypatch.setitem(sys.modules, "flask", fake_flask)
    with patch("core.logger.logging.getLogger") as mock_get:
        mock_logger = MagicMock()
        mock_get.return_value = mock_logger
        log_with_trace("default level test")
        mock_logger.info.assert_called_once()
