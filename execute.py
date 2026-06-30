#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动主脚本
"""
import subprocess
import sys
import os

# 设置编码
if sys.platform == 'win32':
    import locale
    locale.setlocale(locale.LC_ALL, 'Chinese_People\'s Republic of China.936')

# 使用系统默认编码
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 直接导入并运行
sys.path.insert(0, r"d:\yuan\不锈钢网带跟单3.0")

# 导入主脚本
import importlib.util
spec = importlib.util.spec_from_file_location("main_runner", r"d:\yuan\不锈钢网带跟单3.0\main_runner.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
