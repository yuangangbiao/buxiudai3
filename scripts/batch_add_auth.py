# -*- coding: utf-8 -*-
"""
自动扫描 server.py, 给所有未鉴权的写操作路由加 @require_auth + @verify_csrf_token
小钰 2026-06-23 P0 鉴权修复
"""
import re
import sys


def find_routes(src):
    """扫描所有 POST/PUT/DELETE 路由, 收集其后的装饰器."""
    # 找路由: @app.route('...', methods=[...]) 紧接若干 @xxx 装饰器, 然后 def xxx
    pattern = re.compile(
        r"@app\.route\(\s*'([^']+)'\s*,\s*methods=\[([^\]]+)\]\s*\)\s*\n"
        r"((?:@[\w.]+(?:\([^)]*\))?\s*\n)*)"
        r"def\s+(\w+)\s*\("
    )
    routes = []
    for m in pattern.finditer(src):
        path = m.group(1)
        methods = [s.strip().strip("'\"") for s in m.group(2).split(',')]
        decs = m.group(3)
        func = m.group(4)
        write_methods = {'POST', 'PUT', 'DELETE'}
        is_write = bool(set(methods) & write_methods)
        has_auth = '@require_auth' in decs or '@require_role' in decs
        has_csrf = '@verify_csrf_token' in decs
        routes.append({
            'path': path,
            'methods': methods,
            'is_write': is_write,
            'has_auth': has_auth,
            'has_csrf': has_csrf,
            'func': func,
            'span': (m.start(3), m.end(3)),
        })
    return routes


def main():
    path = 'desktop_web/server.py'
    with open(path, 'r', encoding='utf-8') as f:
        src = f.read()

    routes = find_routes(src)
    print(f'共扫描 {len(routes)} 个路由')

    # 写操作 + 未鉴权 (排除 /api/login)
    need_auth = [r for r in routes if r['is_write'] and not r['has_auth'] and r['path'] != '/api/login']
    print(f'需加鉴权的写操作: {len(need_auth)}')

    # 写操作 + 已鉴权但缺 CSRF
    need_csrf = [r for r in routes if r['is_write'] and r['has_auth'] and not r['has_csrf'] and r['path'] != '/api/login']
    print(f'已鉴权但缺 CSRF 的: {len(need_csrf)}')

    # 输出详情
    for r in need_auth:
        print(f'  [-] {r["path"]:<55s} {r["methods"]} -> {r["func"]}()')
    for r in need_csrf:
        print(f'  [~] {r["path"]:<55s} {r["methods"]} -> {r["func"]}()  (缺 CSRF)')

    # 在 src 中批量加装饰器 (从后往前避免行号偏移)
    # 策略: 对每个未鉴权路由, 在其 def 前插入 @require_auth + @verify_csrf_token
    # 对缺 CSRF 的, 仅在 def 前插入 @verify_csrf_token
    inserts = []
    for r in need_auth:
        inserts.append((r['func'], 2))  # 加 require_auth + verify_csrf_token
    for r in need_csrf:
        inserts.append((r['func'], 1))  # 仅加 verify_csrf_token

    n_modified = 0
    n_skipped = 0
    for func_name, kind in inserts:
        # 找 def func_name 行
        pat = re.compile(r"^(def\s+" + re.escape(func_name) + r"\s*\([^)]*\)\s*:\s*)$", re.MULTILINE)
        m = pat.search(src)
        if not m:
            print(f'  [WARN] 未找到 {func_name} def 行')
            n_skipped += 1
            continue
        insert_pos = m.start(1)
        if kind == 2:
            new_decs = '@require_auth\n@verify_csrf_token\n'
        else:
            new_decs = '@verify_csrf_token\n'
        src = src[:insert_pos] + new_decs + src[insert_pos:]
        n_modified += 1

    print(f'\n共修改 {n_modified} 个路由, 跳过 {n_skipped}')

    with open(path, 'w', encoding='utf-8') as f:
        f.write(src)
    print('已写入 server.py')


if __name__ == '__main__':
    main()
