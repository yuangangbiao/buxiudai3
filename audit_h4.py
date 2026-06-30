# -*- coding: utf-8 -*-
"""H4 污染链路审计脚本"""
import os, sys

sys.path.insert(0, r'd:\yuan\不锈钢网带跟单3.0')
sys.path.insert(0, r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai')

print('=== Step 1: sys.path 前3项 ===')
for i, p in enumerate(sys.path[:3]):
    print(f'  [{i}] {p}')

print()
print('=== Step 2: 导入 mobile_api_ai.services (模拟 collection 阶段) ===')
try:
    import mobile_api_ai.services
    print('  OK - mobile_api_ai.services imported')
    print('  __path__:', list(mobile_api_ai.services.__path__))
    print('  __file__:', getattr(mobile_api_ai.services, '__file__', 'None'))
except Exception as e:
    print('  Error:', e)

print()
print('=== Step 3: sys.modules 中的 services 相关 ===')
for name in sorted(sys.modules.keys()):
    if 'services' in name and not name.startswith('_'):
        mod = sys.modules[name]
        f = getattr(mod, '__file__', None)
        p = getattr(mod, '__path__', None)
        print(f'  {name}:')
        print(f'    __file__ = {f}')
        print(f'    __path__ = {p}')

print()
print('=== Step 4: 模拟 clean_polluting_modules ===')
cleared = []
for name in list(sys.modules.keys()):
    mod = sys.modules.get(name)
    if mod is None:
        continue
    if name in {'services'}:
        mod_path = getattr(mod, '__path__', None)
        if mod_path is None and getattr(mod, '__file__', None) is None:
            del sys.modules[name]
            cleared.append(name)
            continue
        if mod_path:
            paths = list(mod_path) if hasattr(mod_path, '__iter__') else [mod_path]
            if any('tests' in str(p).replace('\\', '/').split('/') for p in paths):
                del sys.modules[name]
                cleared.append(name)
print('  cleared (simulated):', cleared)

print()
print('=== Step 5: sys.modules 中的 services 相关（模拟清理后） ===')
for name in sorted(sys.modules.keys()):
    if 'services' in name and not name.startswith('_'):
        mod = sys.modules[name]
        f = getattr(mod, '__file__', None)
        p = getattr(mod, '__path__', None)
        print(f'  {name}:')
        print(f'    __file__ = {f}')
        print(f'    __path__ = {p}')

print()
print('=== Step 6: sys.modules 中 services 子模块（模拟清理后仍残留） ===')
for name in sorted(sys.modules.keys()):
    if 'services.' in name:
        mod = sys.modules[name]
        f = getattr(mod, '__file__', None)
        print(f'  {name}: __file__={f}')

print()
print('=== Step 7: 模拟测试执行阶段导入 services ===')
import services
print('  services imported')
print('  __file__:', getattr(services, '__file__', 'None'))
print('  __path__:', list(getattr(services, '__path__', [])))

print()
print('=== Step 8: services 命名空间内容 ===')
for n in sorted(dir(services)):
    if not n.startswith('_'):
        print(f'  {n}')

print()
print('=== Step 9-13: 各子模块导入验证 ===')
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
        print(f'  OK: {module_name}.{attr_name} = {val}')
    except Exception as e:
        print(f'  FAIL: {module_name}.{attr_name} - {type(e).__name__}: {e}')

print()
print('=== Step 14: 验证 services.audit_service（isolated，子模块已污染） ===')
import sys as _sys2
# 模拟孤立状态：services 被删除，services.audit_service 残留
_saved = _sys2.modules.get('services.audit_service')
if _saved:
    print(f'  services.audit_service 仍在 sys.modules: {_saved.__file__}')
    print('  但父包 services 已被删除，这是孤立模块')
    print('  import services.audit_service 会尝试修复父包，但因相对导入失败')
try:
    import services.audit_service
    print('  OK')
except Exception as e:
    print(f'  FAIL: {type(e).__name__}: {e}')

print()
print('=== 结论 ===')
