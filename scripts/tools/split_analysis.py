#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
C2 拆分分析脚本 — 分析 _core.py 的 Part 归属和导入依赖

用途：
  运行后输出每个 Part 需要导入到 _services.py 的服务函数清单，
  用于一次性生成所有路由文件的 import 语句。

输出示例：
  Part 4:
      _get_client,
      _send_wechat_app_message,
      _notify_with_template,
  ...
"""
import ast
import re
from collections import defaultdict

SRC = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\dispatch_center\_core.py'

with open(SRC, encoding='utf-8') as f:
    content = f.read()

lines = content.splitlines()
tree = ast.parse(content, filename=SRC)

# Step 1: 建立行号 → Part 编号映射
part_markers = {}  # line_number → part_num
for i, line in enumerate(lines, 1):
    m = re.match(r'# Part ([0-9.]+):', line)
    if m:
        part_markers[i] = m.group(1)

# Step 2: 确定每个函数定义的 Part
# 策略：找每个函数定义所在行之前最近的 Part 标记
sorted_parts = sorted(part_markers.keys())  # [228, 5052, ...]

def get_part_for_line(lineno):
    """找小于等于 lineno 的最大 Part 标记行号"""
    result = None
    for p_line in sorted_parts:
        if p_line <= lineno:
            result = part_markers[p_line]
        else:
            break
    return result

# Step 3: 找所有服务函数（不在任何路由中定义的函数）
# 路由函数 = 有 route 装饰器的函数（而非 Part 标记后定义的所有函数）
routed_funcs = {}  # name → part (只包含有 route 装饰器的)

for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        part = get_part_for_line(node.lineno)
        if part:
            # 检查是否有 route 装饰器
            has_route = False
            for dec in node.decorator_list:
                try:
                    dec_src = ast.unparse(dec)
                except Exception:
                    dec_src = ''
                if 'route' in dec_src or 'before_request' in dec_src:
                    has_route = True
                    break
            if has_route:
                routed_funcs[node.name] = part

# service_funcs = 所有函数定义 - 有路由装饰器的函数
all_func_names = set()
for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        all_func_names.add(node.name)

service_funcs = all_func_names - set(routed_funcs.keys())

# Step 4: 找每个路由函数调用的服务函数
route_imports = defaultdict(set)  # part → set of service funcs

for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in routed_funcs:
        part = routed_funcs[node.name]
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and child.id in service_funcs:
                route_imports[part].add(child.id)

# Step 5: 找模块级变量（_dispatch_cache 等）
# 从 __init__.py 的导入语句反推哪些变量是模块级共享状态
# 这些需要进入 _services.py
module_vars = set(re.findall(r'^_([a-z_][a-z0-9_]*)\s*[:=]', content, re.MULTILINE))
# 过滤掉函数定义
module_vars -= service_funcs
module_vars -= set(routed_funcs.keys())

print("=== 每个 Part 需要导入的服务函数 ===\n")

def part_sort_key(x):
    try:
        return float(x.split('.')[0]) if '.' in x else float(x)
    except ValueError:
        return 999

for part in sorted(route_imports.keys(), key=part_sort_key):
    funcs = sorted(route_imports[part])
    print(f"Part {part}:")
    for f in funcs:
        print(f"    {f},")
    print()

print("=== 模块级共享变量（建议进入 _services.py）===\n")
for v in sorted(module_vars):
    if not v.startswith('__'):
        print(f"    {v},")
