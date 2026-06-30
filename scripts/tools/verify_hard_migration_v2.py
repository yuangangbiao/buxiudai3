# -*- coding: utf-8 -*-
"""F22 行动项 3 硬迁移后验证脚本 v2"""
import os
import sys
import py_compile
import ast
import re
from pathlib import Path

os.chdir(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai')
sys.path.insert(0, os.getcwd())

print('=' * 60)
print('F22 行动项 3 硬迁移验收 v2 (2026-06-20)')
print('=' * 60)

# 1. py_compile 检查所有修改过的文件
print()
print('--- 1. 语法检查 ---')
files = [
    'container_center/services/alert_engine.py',
    'container_center/client/container_client.py',
    'container_center_api.py',
    'dispatch_center/_core.py',
    'commands/outsource_cmd.py',
    'container_center_v5.py',
    'wechat_app_bot.py',
    'tests/integration/test_cc_aux.py',
]
fail = False
for f in files:
    try:
        py_compile.compile(f, doraise=True)
        print(f'  [OK] {f}')
    except py_compile.PyCompileError as e:
        print(f'  [FAIL] {f}: {e}')
        fail = True
if fail:
    sys.exit(1)

# 2. AST 验证 AlertEngine 拆分
print()
print('--- 2. AlertEngine 拆分验证 ---')
tree = ast.parse(open('container_center/services/alert_engine.py').read())
for cls in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == 'AlertEngine']:
    check_methods = [f.name for f in cls.body if isinstance(f, ast.FunctionDef) and f.name.startswith('check_')]
    print(f'  AlertEngine.check_* 方法数: {len(check_methods)}')
    required = {'check_overdue_task_alerts', 'check_order_overdue_alerts', 'check_order_timeout_alerts'}
    actual = set(check_methods)
    missing = required - actual
    if missing:
        print(f'  [FAIL] 缺失拆分方法: {missing}')
        sys.exit(1)
    else:
        print(f'  [OK] check_order_timeout_alerts 已拆分为 2 个独立方法')

# 3. AST 验证 ContainerCenterClient 不再有 try/except 回退
print()
print('--- 3. ContainerCenterClient 无 try/except 兜底验证 ---')
tree2 = ast.parse(open('container_center/client/container_client.py').read())
for cls in [n for n in ast.walk(tree2) if isinstance(n, ast.ClassDef) and n.name == 'ContainerCenterClient']:
    for method in [m for m in cls.body if isinstance(m, ast.FunctionDef) and 'alert' in m.name.lower()]:
        has_try = any(isinstance(s, ast.Try) for s in ast.walk(method))
        if has_try:
            print(f'  [FAIL] {method.name} 仍含 try/except 兜底')
            sys.exit(1)
        else:
            print(f'  [OK] {method.name} 无 try/except 兜底')

# 4. AST 验证 container_center_api.py 不再有 /api/v4/alerts
print()
print('--- 4. 容器中心 mock 路由删除验证 ---')
tree3 = ast.parse(open('container_center_api.py').read())
found_v4_alerts = False
for route in [n for n in tree3.body if isinstance(n, ast.FunctionDef) and n.decorator_list]:
    for dec in route.decorator_list:
        if isinstance(dec, ast.Call) and hasattr(dec.func, 'attr') and dec.func.attr == 'route':
            if dec.args:
                path = dec.args[0].value if hasattr(dec.args[0], 'value') else str(dec.args[0])
                if 'v4' in str(path) and 'alert' in str(path):
                    found_v4_alerts = True
                    print(f'  [FAIL] 容器中心仍有 v4 告警路由: {path}')
if found_v4_alerts:
    sys.exit(1)
print('  [OK] 容器中心 /api/v4/alerts 已完全删除')

# 5. 验证死代码包 container_center/api/ 已删除
print()
print('--- 5. 死代码包删除验证 ---')
api_dir = Path('container_center/api')
if api_dir.exists():
    remaining = list(api_dir.glob('*'))
    if remaining:
        print(f'  [FAIL] container_center/api/ 仍有 {len(remaining)} 个文件: {remaining}')
        sys.exit(1)
    else:
        print('  [OK] container_center/api/ 目录为空')
        api_dir.rmdir()
        print('  [OK] 已删除空目录')
else:
    print('  [OK] container_center/api/ 目录不存在')

# 6. 验证 5003 端口告警 API 完整（用 grep）
print()
print('--- 6. 5003 端口告警 API 完整性 ---')
src_core = open('dispatch_center/_core.py').read()
required_alerts = [
    ("/alerts (GET)", r"@dispatch_center_bp\.route\('/alerts'"),
    ("/alerts/<id>/dismiss (POST)", r"@dispatch_center_bp\.route\('/alerts/<alert_id>/dismiss'"),
    ("/alerts/stats (GET)", r"@dispatch_center_bp\.route\('/alerts/stats'"),
    ("/alerts/<id>/ack (POST)", r"@dispatch_center_bp\.route\('/alerts/<alert_id>/ack'"),
    ("/alerts/<id>/snooze (POST)", r"@dispatch_center_bp\.route\('/alerts/<alert_id>/snooze'"),
]
for name, pat in required_alerts:
    m = re.search(pat, src_core)
    if m:
        line = src_core[:m.start()].count('\n') + 1
        print(f'  [OK] {name} (行 {line})')
    else:
        print(f'  [FAIL] {name} 缺失')

# 7. 验证 5003 端口同步 API 完整
print()
print('--- 7. 5003 端口同步 API 完整性 ---')
required_sync = [
    ("/sync/material", r"@dispatch_center_bp\.route\('/sync/material'"),
    ("/sync/repair", r"@dispatch_center_bp\.route\('/sync/repair'"),
    ("/sync/outsource", r"@dispatch_center_bp\.route\('/sync/outsource'"),
    ("/sync/sub-step-report", r"@dispatch_center_bp\.route\('/sync/sub-step-report'"),
    ("/sync/quality-record", r"@dispatch_center_bp\.route\('/sync/quality-record'"),
]
for name, pat in required_sync:
    m = re.search(pat, src_core)
    if m:
        line = src_core[:m.start()].count('\n') + 1
        print(f'  [OK] {name} (行 {line})')
    else:
        print(f'  [FAIL] {name} 缺失')

# 8. 验证测试文件已更新为 404 验证
print()
print('--- 8. 测试更新验证 ---')
src_test = open('tests/integration/test_cc_aux.py').read()
if 'test_v4_alerts_removed' in src_test and 'test_v4_alerts_empty' not in src_test:
    print('  [OK] test_v4_alerts 已改为 404 验证测试')
else:
    print('  [FAIL] 测试未更新')

print()
print('=' * 60)
print('硬迁移验收 v2 完成 ✅')
print('=' * 60)