# -*- coding: utf-8 -*-
"""
Re-export shim: utils.op_logger（2026-06-15 P0 修复）

原 mobile_api_ai/utils/op_logger.py（1831 字节）是功能不完整的 stub，
缺少 log_match / log_calc / log_ui，且函数签名与项目根 utils/op_logger.py
不一致（1984 字节）。当 pytest 将 mobile_api_ai/ 插入 sys.path 时，
该 stub 被优先加载，导致 test_process_calc_rule.py 等测试出现
    ImportError: cannot import name 'log_match' from 'utils.op_logger'

本 shim 用 importlib.util 从项目根显式加载根版本（绕过 sys.path 顺序），
并 re-export 全部公开 API，行为与根版本完全一致。

替换 auto_schema.py 的成功模式（同样用 importlib.util 加载根版本）。
"""
import os
import importlib.util
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ROOT_OP_LOGGER_PATH = os.path.join(_PROJECT_ROOT, 'utils', 'op_logger.py')

_spec = importlib.util.spec_from_file_location(
    'utils.op_logger.project_root', _ROOT_OP_LOGGER_PATH
)
_root_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_root_module)

log = _root_module.log
log_step = _root_module.log_step
log_calc = _root_module.log_calc
log_match = _root_module.log_match
log_sql = _root_module.log_sql
log_error = _root_module.log_error
log_ui = _root_module.log_ui

__all__ = [
    'log', 'log_step', 'log_calc', 'log_match',
    'log_sql', 'log_error', 'log_ui',
]


def __getattr__(name):
    try:
        return getattr(_root_module, name)
    except AttributeError:
        raise AttributeError(
            f"module '{__name__}' has no attribute '{name}'"
        ) from None


def __dir__():
    return sorted(set(__all__ + dir(_root_module)))
