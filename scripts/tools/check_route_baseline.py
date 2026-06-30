# -*- coding: utf-8 -*-
"""Phase 7 零回归 - 路由基线对比（含 Blueprint url_prefix）"""
import os
import re
from pathlib import Path

# 自动定位 mobile_api_ai 目录
SCRIPT_DIR = Path(__file__).resolve().parent
CANDIDATES = [
    SCRIPT_DIR / 'mobile_api_ai',                  # scripts/tools/../mobile_api_ai
    SCRIPT_DIR.parent / 'mobile_api_ai',           # scripts/../mobile_api_ai
    SCRIPT_DIR.parent.parent / 'mobile_api_ai',    # ../../mobile_api_ai
    Path.cwd() / 'mobile_api_ai',                  # cwd/mobile_api_ai
    Path.cwd(),                                    # cwd 直接
]
TARGET_DIR = None
for c in CANDIDATES:
    if c.exists() and (c / 'container_center_api.py').exists():
        TARGET_DIR = c
        break

if TARGET_DIR is None:
    print(f'❌ 无法定位 mobile_api_ai 目录')
    print(f'  尝试: {[str(c) for c in CANDIDATES]}')
    raise SystemExit(1)

print(f'✅ 工作目录: {TARGET_DIR}')
os.chdir(TARGET_DIR)

ROUTES = []
BP_PREFIXES = {}  # bp_name -> prefix

for py_file in Path('.').rglob('*.py'):
    pstr = str(py_file).replace('\\', '/')
    if '_archive' in pstr or '/tests/' in pstr:
        continue
    try:
        content = py_file.read_text(encoding='utf-8')
    except Exception:
        continue

    # 提取 Blueprint url_prefix
    for m in re.finditer(r'Blueprint\(\s*[\'"](\w+)[\'"].*?url_prefix\s*=\s*[\'"]([^\'"]+)[\'"]', content, re.DOTALL):
        BP_PREFIXES[m.group(1)] = m.group(2)

    # 提取路由
    pattern = r'@(\w+)\.route\(\s*[\'"]([^\'"]+)[\'"]'
    for m in re.finditer(pattern, content):
        bp_var = m.group(1)
        path = m.group(2)
        line = content[:m.start()].count('\n') + 1
        # 修复：路由装饰器用的是变量名（如 dispatch_center_bp），但 BP_PREFIXES
        # 用 Blueprint 第一个参数（如 'dispatch_center'）。自动剥离 _bp / _blueprint 后缀。
        bp_name = bp_var
        for suffix in ('_bp', '_blueprint'):
            if bp_name.endswith(suffix):
                bp_name = bp_name[:-len(suffix)]
                break
        prefix = BP_PREFIXES.get(bp_name, '')
        full_path = prefix + path if prefix else path
        ROUTES.append((full_path, bp_name, pstr, line))

unique_paths = sorted(set(r[0] for r in ROUTES))
print(f'Blueprint 注册数: {len(BP_PREFIXES)}')
for k, v in BP_PREFIXES.items():
    print(f'  - {k}: {v}')
print()
print(f'总路由数（含蓝图前缀）: {len(unique_paths)}')
print()
print('=== 关键路由确认（修改后必须仍在）===')
checks = [
    '/api/dispatch-center/alerts',
    '/api/dispatch-center/alerts/<alert_id>/dismiss',
    '/api/dispatch-center/alerts/<alert_id>/ack',
    '/api/dispatch-center/alerts/<alert_id>/snooze',
    '/api/dispatch-center/alerts/stats',
    '/api/dispatch-center/sync/material',
    '/api/dispatch-center/sync/repair',
    '/api/dispatch-center/sync/outsource',
    '/api/dispatch-center/sync/sub-step-report',
    '/api/dispatch-center/sync/quality-record',
    '/api/v4/alerts',
]
for c in checks:
    found = c in unique_paths
    print(f'  {"OK" if found else "FAIL"} {c}')

print()
print('=== 5003 端口告警 API（行动项 3 合并目标）===')
for r in unique_paths:
    if 'dispatch-center' in r and 'alert' in r:
        print(f'  - {r}')

print()
print('=== 5002 端口告警 API（已废弃但保留 90 天软迁移）===')
for r in unique_paths:
    if 'v4' in r and 'alert' in r:
        print(f'  - {r}')