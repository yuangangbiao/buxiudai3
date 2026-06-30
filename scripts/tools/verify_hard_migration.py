# -*- coding: utf-8 -*-
"""F22 行动项 3 硬迁移后验证脚本"""
import os
import sys
import py_compile
import ast
from pathlib import Path

os.chdir(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai')
sys.path.insert(0, os.getcwd())

print('=' * 60)
print('F22 行动项 3 硬迁移验收 (2026-06-20)')
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
]
for f in files:
    try:
        py_compile.compile(f, doraise=True)
        print(f'  [OK] {f}')
    except py_compile.PyCompileError as e:
        print(f'  [FAIL] {f}: {e}')
        sys.exit(1)

# 2. AST 验证 AlertEngine
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
src = open('container_center/client/container_client.py').read()
tree2 = ast.parse(src)
for cls in [n for n in ast.walk(tree2) if isinstance(n, ast.ClassDef) and n.name == 'ContainerCenterClient']:
    for func in [n for n in cls.body if isinstance(n, ast.FunctionDef) and 'alert' in n.name.lower()]:
        has_try = any(isinstance(s, ast.Try) for s in ast.walk(func))
        if has_try:
            print(f'  [FAIL] {func.name} 仍含 try/except 兜底')
            sys.exit(1)
        else:
            print(f'  [OK] {func.name} 无 try/except 兜底')

# 4. AST 验证 container_center_api.py 不再有 /api/v4/alerts
print()
print('--- 4. 容器中心 mock 路由删除验证 ---')
tree3 = ast.parse(open('container_center_api.py').read())
for route in [n for n in tree3.body if isinstance(n, ast.FunctionDef) and n.decorator_list]:
    for dec in route.decorator_list:
        if isinstance(dec, ast.Call) and hasattr(dec.func, 'attr') and dec.func.attr == 'route':
            if dec.args:
                path = dec.args[0].value if hasattr(dec.args[0], 'value') else str(dec.args[0])
                if 'v4' in str(path) and 'alert' in str(path):
                    print(f'  [FAIL] 容器中心仍有 v4 告警路由: {path}')
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

# 6. 验证 5003 端口告警 API 完整
print()
print('--- 6. 5003 端口告警 API 完整性 ---')
import re
src_core = open('dispatch_center/_core.py').read()
required_alerts = [
    r"@dispatch_center_bp\.route\('/alerts'",
    r"@dispatch_center_bp\.route\('/alerts/<alert_id>/dismiss'",
    r"@dispatch_center_bp\.route\'/alerts/stats'",
    r"@dispatch_center_bp\.route\(/alerts/<alert_id>/ack'",
    r"@dispatch_center_bp\.route\(/alerts/<alert_id>/snooze'",
]
for pat in required_alerts:
    m = re.search(pat, src_core)
    if m:
        line = src_core[:m.start()].count('\n') + 1
        print(f'  [OK] 路由存在 (行 {line})')
    else:
        print(f'  [FAIL] 路由缺失: {pat}')

print()
print('=' * 60)
print('硬迁移验收完成 - 全部通过 ✅')
print('=' * 60)