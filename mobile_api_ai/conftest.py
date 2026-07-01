# -*- coding: utf-8 -*-
"""
pytest 全局配置
[F6 P8 2026-06-10] 注入项目根到 sys.path, 让 storage_layer 的 `from core.config import DB_PATHS` 能解析
"""
import os
import sys

_PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
