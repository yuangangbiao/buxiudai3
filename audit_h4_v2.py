# -*- coding: utf-8 -*-
"""H4 污染链路 v2：精确复现 pytest 执行顺序"""
import os, sys

_PROJECT_ROOT = r'd:\yuan\不锈钢网带跟单3.0'
_MOBILE_API_AI = os.path.join(_PROJECT_ROOT, 'mobile_api_ai')

# 模拟 pytest 初始 sys.path (conftest.py 配置后)
sys.path = [_PROJECT_ROOT, _MOBILE_API_AI, r'd:\yuan\不锈钢网带跟单3.0\tests']

print('=== Initial sys.path ===')
for i, p in enumerate(sys.path):
    print(f'  [{i}] {p}')

print()
print('=== Step 1: 模拟 test_process_code_classifier.py 的 sys.path.insert ===')
sys.path.insert(0, os.path.join(_PROJECT_ROOT, 'mobile_api_ai'))
print('  sys.path[0]:', sys.path[0])
print('  sys.path[1]:', sys.path[1])

print()
print('=== Step 2: 导入 mobile_api_ai.core_lib.process_code_classifier ===')
try:
    import mobile_api_ai.core_lib.process_code_classifier
    print('  OK')
except Exception as e:
    print(f'  Error: {e}')

print()
print('=== Step 3: sys.modules 中的 mobile_api_ai.* 列表 ===')
for name in sorted(sys.modules.keys()):
    if name.startswith('mobile_api_ai'):
        mod = sys.modules[name]
        f = getattr(mod, '__file__', None)
        p = getattr(mod, '__path__', None)
        has_file = hasattr(mod, '__file__') and mod.__file__ is not None
        print(f'  {name}:')
        print(f'    __file__ = {f}')
        print(f'    __path__ = {p}')
        print(f'    has __file__ attr (not None) = {has_file}')

print()
print('=== Step 4: 模拟 clean_polluting_modules (同 conftest_helpers) ===')
_TESTS_NORM = os.path.normcase(r'd:\yuan\不锈钢网带跟单3.0\tests')

cleaned_path = []
for p in sys.path:
    if not p:
        cleaned_path.append(p)
        continue
    p_norm = os.path.normcase(p)
    if p_norm == _TESTS_NORM or p_norm.startswith(_TESTS_NORM + os.sep):
        continue
    cleaned_path.append(p)
sys.path[:] = cleaned_path

print('  After path cleanup:')
for i, p in enumerate(sys.path[:5]):
    print(f'    [{i}] {p}')

cleared = []
for cached_name in ['core', 'models', 'services', 'utils']:
    if cached_name in sys.modules:
        cached = sys.modules[cached_name]
        should_clear = False
        if hasattr(cached, '__path__'):
            paths = list(cached.__path__)
            if any('tests' in p.replace('\\', '/').split('/') for p in paths):
                should_clear = True
        elif not hasattr(cached, '__file__') or cached.__file__ is None:
            should_clear = True
        if should_clear:
            del sys.modules[cached_name]
            cleared.append(cached_name)
print(f'  cleared modules: {cleared}')

print()
print('=== Step 5: sys.modules 中的 mobile_api_ai.* (清理后) ===')
for name in sorted(sys.modules.keys()):
    if name.startswith('mobile_api_ai'):
        mod = sys.modules[name]
        f = getattr(mod, '__file__', None)
        p = getattr(mod, '__path__', None)
        print(f'  {name}: __file__={f}, __path__={p}')

print()
print('=== Step 6: 模拟 test_push_50.py 执行 ===')
print('  import services:')
import services
print('    __file__:', getattr(services, '__file__', None))
print('    __path__:', list(getattr(services, '__path__', [])))
print()
print('  dir(services) [not underscore]:')
for n in sorted(dir(services)):
    if not n.startswith('_'):
        print(f'    {n}')

print()
print('=== Step 7: 验证各子模块 ===')
test_cases = [
    ('services.audit_service', 'AuditService'),
    ('services.schedule_dispatch_service', 'ScheduleDispatchService'),
    ('services.wechat_report_service', 'WeChatReportService'),
    ('services.inventory_notifier', 'InventoryNotifier'),
    ('services.inventory_sync', 'inventory_sync'),
]
for module_name, attr_name in test_cases:
    try:
        mod = __import__(module_name, fromlist=[attr_name])
        val = getattr(mod, attr_name)
        print(f'  OK: {module_name}.{attr_name}')
    except Exception as e:
        print(f'  FAIL: {module_name}.{attr_name} - {type(e).__name__}: {e}')
