# -*- coding: utf-8 -*-
"""深度诊断 - 加载 quality 模块,看其 metrics 究竟指向谁"""
import sys
import os
import importlib.util

PROJECT_ROOT = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai'
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
PARENT_DIR = r'd:\yuan\不锈钢网带跟单3.0'
if PARENT_DIR not in sys.path:
    sys.path.append(PARENT_DIR)

# 模拟 app.py 启动顺序
from mobile_api_ai.api.metrics_api import metrics as m_metrics_api
print(f'before importing quality: m_metrics_api id = {id(m_metrics_api)}')
print(f'before importing quality: sys.modules["metrics"] = {sys.modules.get("metrics")}, id={id(sys.modules.get("metrics"))}')

# 1. 用包路径加载 quality
print('\n[路径A] 加载 mobile_api_ai.api.quality')
from mobile_api_ai.api import quality as q1
print(f'  quality module: {q1.__name__}, file: {q1.__file__}')
print(f'  quality.metrics: {q1.metrics}, id={id(q1.metrics)}')
print(f'  quality.metrics is m_metrics_api? {q1.metrics is m_metrics_api}')
print(f'  quality.metrics is sys.modules["metrics"]? {q1.metrics is sys.modules.get("metrics")}')

# 2. 用文件路径直接加载
print('\n[路径B] 加载 mobile_api_ai.api.quality (再次,应该从缓存)')
import mobile_api_ai.api.quality as q2
print(f'  q1 is q2? {q1 is q2}')

# 3. 现在看 sys.modules
print('\n[step 3] sys.modules 详情')
print(f'  sys.modules["metrics"]: {sys.modules.get("metrics")}, id={id(sys.modules.get("metrics"))}')

# 4. 看 quality 模块的 metrics 是 mobile_api_ai.api.metrics 的吗?
print(f'\n[step 4] mobile_api_ai.api.metrics = {getattr(sys.modules.get("mobile_api_ai.api"), "metrics", "NOT_FOUND")}')

# 5. 看 metrics 模块的属性
m = sys.modules.get('metrics')
if m:
    print(f'\n[step 5] metrics module:')
    print(f'  __file__: {m.__file__}')
    print(f'  __name__: {m.__name__}')
    print(f'  metrics attr: {m.metrics}, id={id(m.metrics)}')
    print(f'  m.metrics is m_metrics_api? {m.metrics is m_metrics_api}')

# 6. 看 quality 模块的 __dict__ 里有几个 metrics 相关
print(f'\n[step 6] quality.__dict__ 里的 metrics 相关:')
for k, v in q1.__dict__.items():
    if 'metric' in k.lower() or 'Metric' in str(type(v)):
        print(f'  {k} = {v}, id={id(v)}')

# 7. 看 globals 里
print(f'\n[step 7] quality globals "metrics": {q1.__dict__.get("metrics", "NOT_FOUND")}')
