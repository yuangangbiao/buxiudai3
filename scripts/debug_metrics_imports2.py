# -*- coding: utf-8 -*-
"""完整模拟 app.py 启动时的导入顺序,验证 metrics 模块加载"""
import sys
import os
import importlib

# 模拟 app.py 的 sys.path 设置
PROJECT_ROOT = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai'
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
PARENT_DIR = r'd:\yuan\不锈钢网带跟单3.0'
if PARENT_DIR not in sys.path:
    sys.path.append(PARENT_DIR)

# 模拟 app.py 启动顺序
print('=== 模拟 app.py 启动顺序 ===\n')

# 1. 先导入 metrics_api (try/except 包内导入)
print('[step 1] 导入 mobile_api_ai.api.metrics_api')
try:
    from mobile_api_ai.api.metrics_api import bp as metrics_bp
    from mobile_api_ai.api.metrics_api import metrics as m_metrics_api
    print(f'  m_metrics_api id = {id(m_metrics_api)}')
except Exception as e:
    print(f'  ERR: {e}')

# 2. 导入 quality (先 import 的)
print('\n[step 2] 导入 mobile_api_ai.api.quality')
try:
    from mobile_api_ai.api import quality
    print(f'  quality.metrics id = {id(quality.metrics)}')
except Exception as e:
    print(f'  ERR: {e}')

# 3. 查 sys.modules
print('\n[step 3] sys.modules 检查')
m_mod = sys.modules.get('metrics')
print(f'  sys.modules["metrics"]: {m_mod}, id={id(m_mod) if m_mod else "None"}')
print(f'  m_metrics_api is sys.modules["metrics"]? {m_metrics_api is m_mod}')
print(f'  quality.metrics is sys.modules["metrics"]? {quality.metrics is m_mod}')

# 4. 列出 metrics 相关模块
print('\n[step 4] 所有 metrics 相关 sys.modules:')
for k in list(sys.modules.keys()):
    if 'metric' in k.lower():
        print(f'  {k} = id={id(sys.modules[k])}')
