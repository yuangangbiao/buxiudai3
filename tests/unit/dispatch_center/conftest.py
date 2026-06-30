# -*- coding: utf-8 -*-
"""
[v3.7.5] unit/dispatch_center 测试 conftest

修复 dispatch_center.__init__.py 中 `from dispatch_center._core import *` 的路径问题。
__init__.py 使用绝对导入 dispatch_center，需要 mobile_api_ai 在 sys.path
让 dispatch_center 可作为顶级包导入。
"""
import sys
import os

_MOBILE_API_AI = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    'mobile_api_ai',
)
if _MOBILE_API_AI not in sys.path:
    sys.path.insert(0, _MOBILE_API_AI)
