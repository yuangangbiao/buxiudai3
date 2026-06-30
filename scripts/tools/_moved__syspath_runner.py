# -*- coding: utf-8 -*-
"""
syspath 配置 - 确保 mobile_api_ai 的模块优先于父项目

此文件不是 pytest conftest，不被 pytest 自动加载。
如需在特定测试中使用，请显式导入。
"""
import os
import sys

_MOBILE_API_AI_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
_PARENT_DIR = os.path.dirname(_MOBILE_API_AI_DIR)

if '' in sys.path:
    sys.path.remove('')

if _PARENT_DIR in sys.path:
    sys.path.remove(_PARENT_DIR)

if _MOBILE_API_AI_DIR not in sys.path:
    sys.path.insert(0, _MOBILE_API_AI_DIR)
