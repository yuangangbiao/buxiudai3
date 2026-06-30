# -*- coding: utf-8 -*-
"""验证 metrics 模块在 api 包内不同位置导入时是否是同一对象"""
import sys
import os

# 模拟 app.py 的 sys.path 设置
PROJECT_ROOT = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai'
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 1. 直接绝对导入
from metrics import metrics as m1
print(f'[1] direct: id={id(m1)} module={m1.__class__.__module__}')

# 2. 通过 mobile_api_ai 包导入
import importlib
ma_pkg = importlib.import_module('mobile_api_ai')
print(f'[2] mobile_api_ai loaded: {ma_pkg.__file__}')

# 3. 通过 mobile_api_ai.api.metrics_api 路径
ma_api_pkg = importlib.import_module('mobile_api_ai.api')
print(f'[3] mobile_api_ai.api loaded: {ma_api_pkg.__file__}')

# 4. quality 模拟：先 import mobile_api_ai.api.quality,然后看它内部的 metrics id
import mobile_api_ai.api.quality as q_mod
print(f'[4] quality module metrics id = {id(q_mod.metrics)}')
print(f'[4] m1 id = {id(m1)}')
print(f'[4] same? {id(q_mod.metrics) == id(m1)}')

# 5. 查 sys.modules
print(f'[5] sys.modules["metrics"] = {sys.modules.get("metrics")}')
print(f'[5] m1 is sys.modules["metrics"]? {m1 is sys.modules.get("metrics")}')
print(f'[5] q_mod.metrics is sys.modules["metrics"]? {q_mod.metrics is sys.modules.get("metrics")}')

# 6. 列出所有 metrics 相关 sys.modules
print(f'[6] metrics-related modules:')
for k in list(sys.modules.keys()):
    if 'metric' in k.lower():
        print(f'    {k} = {sys.modules[k]}')
