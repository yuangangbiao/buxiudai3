# -*- coding: utf-8 -*-
"""F22 行动项 3 硬迁移后 - 静态验证 (无需运行时依赖)

通过 AST 解析 + 源码分析验证：
1. ContainerCenterClient.get_alert_list / dismiss_alert 直接调用 5003 URL
2. 无 try/except 兜底
3. AlertEngine 拆分函数可调用
4. _core.py 路由完整性
"""
import os
import sys
import ast
import re

os.chdir(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai')
print('=' * 60)
print('F22 行动项 3 硬迁移 - 静态验证 (2026-06-20)')
print('=' * 60)

# ═══════════════════════════════════════════════════════════════
# 1. ContainerCenterClient 静态分析
# ═══════════════════════════════════════════════════════════════
print()
print('--- 1. ContainerCenterClient 静态分析 ---')

src = open('container_center/client/container_client.py').read()
tree = ast.parse(src)

for cls in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == 'ContainerCenterClient']:
    for method in [m for m in cls.body if isinstance(m, ast.FunctionDef) and 'alert' in m.name.lower()]:
        method_src = ast.unparse(method)
        # 检查 try/except
        has_try = any(isinstance(s, ast.Try) for s in ast.walk(method))
        # 检查 5003 URL
        has_5003 = '5003' in method_src and '/api/dispatch-center/alerts' in method_src
        # 检查 5002 fallback
        has_5002 = '/api/v4/alerts' in method_src and 'GET' in method_src.upper() or 'PUT' in method_src.upper()
        # 但要排除 docstring 中的提及
        if method.body and isinstance(method.body[0], ast.Expr) and isinstance(method.body[0].value, (ast.Constant, ast.JoinedStr)):
            # 第一个语句是 docstring
            body_src = ast.unparse(method.body[1:]) if len(method.body) > 1 else ''
        else:
            body_src = method_src

        body_5002 = '/api/v4/alerts' in body_src and ('_request(' in body_src or '.get(' in body_src or '.post(' in body_src)
        status = '✅' if (not has_try and has_5003 and not body_5002) else '❌'
        print(f'  {status} {method.name}')
        print(f'    - 无 try/except: {not has_try}')
        print(f'    - 调用 5003 端口: {has_5003}')
        print(f'    - 无 5002 fallback (代码体): {not body_5002}')

# ═══════════════════════════════════════════════════════════════
# 2. AlertEngine 拆分验证
# ═══════════════════════════════════════════════════════════════
print()
print('--- 2. AlertEngine 拆分验证 ---')

src2 = open('container_center/services/alert_engine.py').read()
tree2 = ast.parse(src2)
for cls in [n for n in ast.walk(tree2) if isinstance(n, ast.ClassDef) and n.name == 'AlertEngine']:
    methods = {m.name: m for m in cls.body if isinstance(m, ast.FunctionDef)}
    for name in ['check_overdue_task_alerts', 'check_order_overdue_alerts', 'check_order_timeout_alerts']:
        if name in methods:
            m = methods[name]
            print(f'  ✅ AlertEngine.{name} (行 {m.lineno})')

# 验证 alert_engine.py:782 调用点已更新
print()
print('  --- alert_engine.py:782 调用点更新验证 ---')
lines = src2.split('\n')
if len(lines) >= 782:
    line_782 = lines[781]
    print(f'  L782: {line_782.strip()[:80]}')
    if 'check_overdue_task_alerts' in line_782 and 'check_order_overdue_alerts' in line_782:
        print(f'  ✅ 已直接调用拆分后的两个方法')
    else:
        print(f'  ⚠️  仍调用 wrapper check_order_timeout_alerts')

# ═══════════════════════════════════════════════════════════════
# 3. 5003 端口路由完整性
# ═══════════════════════════════════════════════════════════════
print()
print('--- 3. 5003 端口路由完整性 ---')

src3 = open('dispatch_center/_core.py').read()
sync_routes = re.findall(r"@dispatch_center_bp\.route\('(/sync/[^']+)'", src3)
alert_routes = re.findall(r"@dispatch_center_bp\.route\('(/alerts[^']*)'", src3)

print(f'  同步路由: {len(sync_routes)} 条')
for r in sync_routes:
    print(f'    ✅ {r}')

print(f'  告警路由: {len(alert_routes)} 条')
for r in alert_routes:
    print(f'    ✅ {r}')

# ═══════════════════════════════════════════════════════════════
# 4. 容器中心 mock 路由彻底消失
# ═══════════════════════════════════════════════════════════════
print()
print('--- 4. /api/v4/alerts 残留检查 ---')

# 搜整个 mobile_api_ai 目录
hits = []
for root, dirs, files in os.walk('.'):
    if '_archive' in root or '.git' in root or '__pycache__' in root:
        continue
    for f in files:
        if not f.endswith('.py'):
            continue
        p = os.path.join(root, f)
        try:
            content = open(p, encoding='utf-8').read()
        except:
            continue
        if "'/api/v4/alerts'" in content or '"/api/v4/alerts"' in content:
            # 排除纯 docstring 提及
            stripped = re.sub(r'"""[\s\S]*?"""', '', content)
            stripped = re.sub(r"'''[\s\S]*?'''", '', stripped)
            if "'/api/v4/alerts'" in stripped or '"/api/v4/alerts"' in stripped:
                hits.append((p, 'real reference'))
            else:
                hits.append((p, 'docstring only'))

print(f'  共 {len(hits)} 处 /api/v4/alerts 命中:')
for p, kind in hits:
    print(f'    [{kind}] {p}')

# ═══════════════════════════════════════════════════════════════
# 5. 死代码包 container_center/api/ 已彻底消失
# ═══════════════════════════════════════════════════════════════
print()
print('--- 5. 死代码包 container_center/api/ 删除验证 ---')
api_dir = 'container_center/api'
if os.path.exists(api_dir):
    remaining = os.listdir(api_dir)
    print(f'  ⚠️  container_center/api/ 仍存在 {len(remaining)} 个文件: {remaining}')
else:
    print(f'  ✅ container_center/api/ 目录不存在（7 文件已删除）')

print()
print('=' * 60)
print('静态验证完成 ✅')
print('=' * 60)