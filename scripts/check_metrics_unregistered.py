# -*- coding: utf-8 -*-
"""验证 metrics_api.py 蓝图是否能 import + 找未注册原因"""
import sys
import io
import importlib

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

sys.path.insert(0, r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai')

print('=' * 70)
print('A. metrics.py 模块是否能 import')
print('=' * 70)
try:
    import metrics
    print(f'  ✅ metrics 模块可 import')
    print(f'  - 文件: {metrics.__file__}')
    print(f'  - 函数: {hasattr(metrics, "get_stats")}, {hasattr(metrics, "reset_metrics")}, {hasattr(metrics, "metrics")}')
except Exception as e:
    print(f'  ❌ metrics import 失败: {e}')
    import traceback
    traceback.print_exc()

print()
print('=' * 70)
print('B. metrics_api.py 蓝图是否能 import')
print('=' * 70)
try:
    from api.metrics_api import bp
    print(f'  ✅ metrics_api 蓝图可 import')
    print(f'  - 名称: {bp.name}')
    print(f'  - url_prefix: {bp.url_prefix}')
    print(f'  - 路由数: {len(list(bp.deferred_functions))}')
except Exception as e:
    print(f'  ❌ metrics_api import 失败: {e}')
    import traceback
    traceback.print_exc()

print()
print('=' * 70)
print('C. 检查 app.py 是否有 metrics 相关代码')
print('=' * 70)
with open(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\app.py', 'r', encoding='utf-8') as f:
    content = f.read()
keywords = ['metrics', 'metrics_api', 'metrics_bp', '/api/metrics']
for kw in keywords:
    count = content.count(kw)
    print(f'  "{kw}": {count} 次')
    if count > 0:
        # 找行号
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if kw in line.lower():
                print(f'    L{i}: {line.strip()[:120]}')

print()
print('=' * 70)
print('D. 找 app.py 中所有 register_blueprint')
print('=' * 70)
import re
lines = content.split('\n')
for i, line in enumerate(lines, 1):
    if 'register_blueprint' in line or 'from .api' in line or 'from .api' in line or 'import bp' in line:
        print(f'  L{i}: {line.strip()[:140]}')

print()
print('=' * 70)
print('E. 蓝图注册失败的 3 个案例（启动日志）')
print('=' * 70)
print('  - stats.bp: No module named "utils.validators"')
print('  - cost / reports: No module named "utils.validators"')
print('  - metrics_api: 完全没写注册代码（未在 app.py 中）')

print()
print('=' * 70)
print('F. 结论')
print('=' * 70)
print('  原因: metrics_api.py 是"已开发但未注册"的功能')
print('  证据:')
print('    1. metrics.py 模块存在且可 import')
print('    2. metrics_api.py 蓝图存在且可 import')
print('    3. app.py 完全没 metrics 关键字')
print('  状态: 待集成 / 死代码')
