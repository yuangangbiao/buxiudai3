"""清点项目所有路由 + 业务功能清单"""
import re
import os

PROJECT_ROOT = r'd:\yuan\不锈钢网带跟单3.0'

# 1. 主要 server 文件
SERVER_FILES = [
    r'desktop_web\server.py',
    r'mobile_api_ai\standalone_dispatch_server.py',
    r'mobile_api_ai\app.py',
    r'mobile_api_ai\sync_bridge_server.py',
    r'mobile_api_ai\face_server.py',
    r'mobile_api_ai\api_v1.py',
]

# 2. 蓝图文件
BLUEPRINT_DIRS = [
    r'mobile_api_ai\api',
]

# 3. 桌面端 views（仅菜单文件）
DESKTOP_VIEWS = r'desktop\views'


def count_routes_in_file(filepath):
    """统计单个文件中所有 Flask 路由"""
    full = os.path.join(PROJECT_ROOT, filepath)
    if not os.path.exists(full):
        return None
    with open(full, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    # 匹配 @xxx.route('path', methods=[...])
    pattern = r'@\w+\.route\(\s*[\'"]([^\'"]+)[\'"](?:\s*,\s*methods\s*=\s*\[([^\]]+)\])?\s*\)'
    matches = re.findall(pattern, content)
    return matches


def get_routes_with_method(routes):
    """给路由添加方法名"""
    out = []
    for path, methods in routes:
        if methods:
            m = re.findall(r'[\'"](\w+)[\'"]', methods)
            method_str = ','.join(m)
        else:
            method_str = 'GET'
        out.append((path, method_str))
    return out


def main():
    print('=' * 80)
    print('项目路由清点')
    print('=' * 80)

    total_all = 0
    for f in SERVER_FILES:
        routes = count_routes_in_file(f)
        if routes is None:
            print(f'\n[SKIP] {f} (not found)')
            continue
        formatted = get_routes_with_method(routes)
        total_all += len(formatted)
        print(f'\n=== {f} ===')
        print(f'路由数: {len(formatted)}')
        # 按方法分组
        get_r = [r for r in formatted if 'GET' in r[1] and 'POST' not in r[1]]
        post_r = [r for r in formatted if 'POST' in r[1]]
        put_r = [r for r in formatted if 'PUT' in r[1]]
        del_r = [r for r in formatted if 'DELETE' in r[1]]
        other_r = [r for r in formatted if r[1] not in ('GET', 'POST', 'PUT', 'DELETE') and ',' not in r[1]]
        print(f'  GET: {len(get_r)}')
        print(f'  POST: {len(post_r)}')
        print(f'  PUT: {len(put_r)}')
        print(f'  DELETE: {len(del_r)}')

    # 蓝图目录
    for bd in BLUEPRINT_DIRS:
        bdir = os.path.join(PROJECT_ROOT, bd)
        if not os.path.exists(bdir):
            continue
        print(f'\n=== 蓝图目录 {bd} ===')
        for fn in sorted(os.listdir(bdir)):
            if not fn.endswith('.py') or fn == '__init__.py':
                continue
            full = os.path.join(bdir, fn)
            with open(full, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            # 蓝图路由
            pat = r'@bp\.route\(\s*[\'"]([^\'"]+)[\'"](?:\s*,\s*methods\s*=\s*\[([^\]]+)\])?\s*\)'
            matches = re.findall(pat, content)
            if matches:
                print(f'  {fn}: {len(matches)} routes')
                for path, methods in matches:
                    if methods:
                        m = re.findall(r'[\'"](\w+)[\'"]', methods)
                        ms = ','.join(m)
                    else:
                        ms = 'GET'
                    print(f'    {ms:20s} {path}')

    # 桌面端 views
    print(f'\n=== 桌面端 views ===')
    vdir = os.path.join(PROJECT_ROOT, DESKTOP_VIEWS)
    view_files = []
    for root, _, files in os.walk(vdir):
        for f in files:
            if f.endswith('.py') and not f.startswith('_') and f != '__init__.py':
                view_files.append(os.path.join(root, f))
    for vf in view_files:
        rel = os.path.relpath(vf, PROJECT_ROOT)
        with open(vf, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        # 检查是否是视图类
        class_pat = r'class\s+(\w+)\s*\('
        classes = re.findall(class_pat, content)
        if classes:
            print(f'  {rel}: {len(classes)} classes: {classes[:3]}')

    print('\n' + '=' * 80)
    print(f'总计路由 (server files): {total_all}')
    print('=' * 80)


if __name__ == '__main__':
    main()
