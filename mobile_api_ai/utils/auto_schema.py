# -*- coding: utf-8 -*-
"""
Re-export shim: utils.auto_schema（2026-06-09 -> 06-10 fix #3）

原 mobile_api_ai/utils/auto_schema.py（336 行）与项目根 utils/auto_schema.py
（336 行）功能完全重叠。两者差异：
  - 项目根版本（推荐）：通过 `from core.db import get_direct_connection`
    抽象数据库连接，可测试性更好
  - mobile_api_ai 版本：直接 `import pymysql` 硬连接，不易 mock

本 shim 将 mobile_api_ai 侧的 import 重定向到项目根版本（统一超集）。

设计原则：
  - 默认行为（推荐）：上层代码使用 `from utils.auto_schema import ...`
    （如 storage/mysql_storage.py:15），由 mobile_api_ai/pyproject.toml:31
    的 `pythonpath = [".."]` 解析到项目根版本，本 shim 不会被加载
  - importlib 绕包加载 + __getattr__ 透明转发：当 Python 将 utils 包解析到
    mobile_api_ai/utils/ 时，`from utils.auto_schema import _private_fn` 会
    找到本 shim。模块级 __getattr__ 将未显式定义的属性访问透明转发到项目根
    版本的真实模块，确保所有公开/私有 API 一致可用。
  - 公开 API 与原文件完全一致（包括所有私有函数用于测试）

替代方案（推荐新代码使用）：
    直接 import 项目根版本，跳过 shim：
    from utils.auto_schema import auto_ensure_schema, SafeCursor
"""
import os
import importlib.util
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ROOT_AUTO_SCHEMA_PATH = os.path.join(_PROJECT_ROOT, 'utils', 'auto_schema.py')

_spec = importlib.util.spec_from_file_location(
    'utils.auto_schema.project_root', _ROOT_AUTO_SCHEMA_PATH
)
_root_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_root_module)

auto_ensure_schema = _root_module.auto_ensure_schema
SafeCursor = _root_module.SafeCursor
clear_schema_cache = _root_module.clear_schema_cache
_schema_cache = _root_module._schema_cache
_schema_lock = _root_module._schema_lock

__all__ = ['auto_ensure_schema', 'SafeCursor', 'clear_schema_cache',
           '_schema_cache', '_schema_lock']


def __getattr__(name):
    try:
        return getattr(_root_module, name)
    except AttributeError:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'") from None


def __dir__():
    return sorted(set(__all__ + dir(_root_module)))
