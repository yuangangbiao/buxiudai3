# -*- coding: utf-8 -*-
"""
统一日志系统模块
所有日志必须通过此模块，禁止使用print
"""

import logging
import os
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional

from core.config import BASE_DIR, LOG_DIR


class LogManager:
    """日志管理器"""

    _instance: Optional['LogManager'] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._loggers = {}

        # 确保日志目录存在
        LOG_DIR.mkdir(parents=True, exist_ok=True)

    def _create_logger(self, name: str, level: int = logging.INFO) -> logging.Logger:
        """创建指定名称的logger"""
        logger = logging.getLogger(name)
        logger.setLevel(level)

        # 避免重复添加handler
        if logger.handlers:
            return logger

        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)

        # 文件处理器（按大小轮转）
        log_file = LOG_DIR / f"{name}.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        return logger

    def get_logger(self, name: str) -> logging.Logger:
        """获取指定名称的logger"""
        if name not in self._loggers:
            self._loggers[name] = self._create_logger(name)
        return self._loggers[name]


# 全局日志管理器
log_manager = LogManager()


def get_logger(name: str) -> logging.Logger:
    """
    获取日志记录器

    使用方式:
        logger = get_logger(__name__)
        logger.info("这是一条日志")
        logger.error("错误信息", exc_info=True)
    """
    return log_manager.get_logger(name)


import json as _json
from datetime import datetime as _datetime


class StructuredLogger:
    """结构化日志包装器

    将额外上下文信息编码为 JSON 附加到日志消息末尾，
    便于日志聚合系统（如 ELK、Loki）解析和检索。

    使用方式:
        slog = get_structured_logger(__name__)
        slog.info("订单创建成功", order_no="ORD-001", operator="张三")
        slog.error("操作失败", order_no="ORD-001", error=str(e))
    """

    def __init__(self, logger: logging.Logger):
        """包装一个标准 logging.Logger 实例"""
        self._logger = logger

    def _log(self, level: int, msg: str, **extra) -> None:
        """内部日志方法，将 extra 序列化为 JSON 附加到消息"""
        extra.setdefault("timestamp", _datetime.now().isoformat())
        self._logger.log(
            level,
            f"{msg} | {_json.dumps(extra, ensure_ascii=False, default=str)}"
        )

    def info(self, msg: str, **extra) -> None:
        self._log(logging.INFO, msg, **extra)

    def warning(self, msg: str, **extra) -> None:
        self._log(logging.WARNING, msg, **extra)

    def error(self, msg: str, **extra) -> None:
        self._log(logging.ERROR, msg, **extra)

    def debug(self, msg: str, **extra) -> None:
        self._log(logging.DEBUG, msg, **extra)

    def critical(self, msg: str, **extra) -> None:
        self._log(logging.CRITICAL, msg, **extra)

    def exception(self, msg: str, **extra) -> None:
        """记录异常日志，自动附带 traceback"""
        extra.setdefault("timestamp", _datetime.now().isoformat())
        self._logger.exception(
            f"{msg} | {_json.dumps(extra, ensure_ascii=False, default=str)}"
        )


def get_structured_logger(name: str) -> StructuredLogger:
    """获取结构化日志记录器"""
    return StructuredLogger(logging.getLogger(name))


# ──────────────────────────────────────────────────────────
# trace_id 支持（S5-03）
# ──────────────────────────────────────────────────────────

import uuid as _uuid

_request_id = None


def get_request_id() -> str:
    """获取当前请求的 trace ID。

    优先从 Flask request 头部的 X-Request-ID 获取；
    若无法获取（非请求上下文或无头），生成一个 8 位短 UUID。

    Returns:
        str: 8 字符的 trace ID
    """
    try:
        import flask as _flask
        if _flask.has_request_context():
            rid = _flask.request.headers.get('X-Request-ID', '')
            if rid:
                return rid
    except Exception:
        pass
    return str(_uuid.uuid4())[:8]


def log_with_trace(msg: str, level: str = 'info', **kwargs) -> None:
    """带 trace_id 的日志便捷方法。

    自动在日志消息前附加 [trace_id]，方便跨请求追踪。

    Usage:
        log_with_trace('订单创建成功', level='info', order_no='ORD-001')
        log_with_trace('同步失败', level='error', exc_info=True)

    Args:
        msg: 日志消息
        level: 日志级别，支持 'debug'/'info'/'warning'/'error'/'critical'
        **kwargs: 传递给底层 logger 的额外参数（如 exc_info=True）
    """
    logger = logging.getLogger(__name__)
    rid = get_request_id()
    log_func = getattr(logger, level, logger.info)
    log_func(f"[{rid}] {msg}", **kwargs)
