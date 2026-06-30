# -*- coding: utf-8 -*-
"""
进程 stdout 监控工具 — 根 utils 门面模块

提供 monitor_process_stdout、start_monitor_thread 等函数。
在单元测试环境中（无法真正监控进程时），提供空实现。
"""
import sys as _sys
import os as _os

_project_root = _os.path.dirname(_os.path.abspath(__file__))


def _lazy_import():
    _mobile_utils = _os.path.join(_project_root, 'mobile_api_ai', 'utils')
    if _mobile_utils not in _sys.path:
        _sys.path.insert(0, _mobile_utils)
    try:
        from utils.process_monitor import monitor_process_stdout, start_monitor_thread
        return monitor_process_stdout, start_monitor_thread
    except ImportError:
        return None, None


_monitor, _thread_fn = None, None


def _ensure():
    global _monitor, _thread_fn
    if _monitor is None:
        _monitor, _thread_fn = _lazy_import()


def monitor_process_stdout(process_name=None, lines=5):
    _ensure()
    if _monitor is not None:
        return _monitor(process_name, lines)
    return []


def start_monitor_thread(process_name=None, lines=5, daemon=True):
    _ensure()
    if _thread_fn is not None:
        return _thread_fn(process_name, lines, daemon)
    return None


__all__ = ['monitor_process_stdout', 'start_monitor_thread']
