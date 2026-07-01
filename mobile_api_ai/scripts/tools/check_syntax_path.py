"""容器中心 & 调度中心 语法 + 路径检查"""

import ast
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent.parent

TARGET_FILES = [
    'dispatch_center.py',
    'container_center_api.py',
    'container_center/__init__.py',
    'container_center/client/__init__.py',
    'container_center/client/container_client.py',
    'container_center/services/__init__.py',
    'container_center/services/alert_engine.py',
    'container_center/storage/__init__.py',
    'container_center/storage/document_store.py',
    'container_center/storage/config_store.py',
    'container_center/storage/alert_store.py',
    'container_center/storage/index_store.py',
    'container_center/storage/router.py',
    'container_center/api/__init__.py',
    'container_center/api/app.py',
    'container_center/api/documents.py',
    'container_center/api/configs.py',
    'container_center/api/alerts.py',
    'container_center/api/health.py',
    'config_center.py',
    'config.py',
    'app.py',
]

errors = []
warnings = []

def check_syntax(filepath):
    """AST 语法检查"""
    try:
        source = filepath.read_text('utf-8', errors='replace')
        ast.parse(source)
        return True, None
    except SyntaxError as e:
        return False, f'L{e.lineno}: {e.msg}'

def check_brackets(filepath):
    """括号匹配检查（跳过字符串内容）"""
    try:
        source = filepath.read_text('utf-8', errors='replace')
        stack = []
        pairs = {'(': ')', '[': ']', '{': '}'}
        closes = {')': '(', ']': '[', '}': '{'}
        in_string = False
        string_char = None
        for i, ch in enumerate(source):
            if in_string:
                if ch == '\\':
                    continue
                if ch == string_char:
                    in_string = False
                continue
            if ch in ('"', "'", '`'):
                in_string = True
                string_char = ch
                continue
            if ch in pairs:
                stack.append((ch, i))
            elif ch in closes:
                if not stack:
                    return False, f'pos {i}: 多余的 {ch}'
                last, pos = stack.pop()
                if pairs[last] != ch:
                    return False, f'pos {i}: {ch} 不匹配 pos {pos} 的 {last}'
        if stack:
            last, pos = stack[0]
            return False, f'pos {pos}: 未闭合的 {last}'
        return True, None
    except Exception as e:
        return False, str(e)

def check_hardcoded_paths(filepath):
    """硬编码路径检查"""
    try:
        source = filepath.read_text('utf-8', errors='replace')
        issues = []

        # Windows 绝对路径
        win_paths = re.findall(r'["\']([A-Za-z]:\\[^"\']{3,})["\']', source)
        for p in win_paths:
            if 'BASE_DIR' not in p and 'os.path' not in p and '__file__' not in p:
                issues.append(f'Windows 绝对路径: {p}')

        # Linux 绝对路径
        linux_paths = re.findall(r'["\'](/data/|/app/|/home/|/root/|/var/|/etc/|/tmp/|/opt/)[^"\']+["\']', source)
        for p in linux_paths:
            issues.append(f'Linux 绝对路径: {p}')

        # os.path.join(__file__, ...) 模式
        file_joins = re.findall(r'os\.path\.join\(\s*__file__\s*,', source)
        if file_joins:
            issues.append(f'os.path.join(__file__,...) 模式: {len(file_joins)} 处')

        # open() 硬编码路径
        open_paths = re.findall(r'open\(["\']([^"\']+)["\']\)', source)
        for p in open_paths:
            if p not in ('.env', '.env.example', 'requirements.txt'):
                issues.append(f'open() 硬编码: {p}')

        return len(issues) == 0, issues
    except Exception as e:
        return False, [str(e)]

def check_import_paths(filepath):
    """导入路径检查"""
    try:
        source = filepath.read_text('utf-8', errors='replace')
        issues = []

        # sys.path.insert/append
        sys_paths = re.findall(r'sys\.path\.(insert|append)\([^)]+\)', source)
        for s in sys_paths:
            issues.append(f'sys.path 操作: {s}')

        return len(issues) == 0, issues
    except Exception as e:
        return False, [str(e)]


def main():
    print('=' * 60)
    print('  容器中心 & 调度中心 语法/路径检查')
    print('=' * 60)
    print()

    total_ok = 0
    total_fail = 0

    for rel in TARGET_FILES:
        fp = BASE / rel
        if not fp.exists():
            print(f'  SKIP  {rel} (文件不存在)')
            continue

        print(f'--- {rel} ---')

        # 1. AST 语法
        ok, err = check_syntax(fp)
        if ok:
            print(f'  [OK] AST 语法')
            total_ok += 1
        else:
            print(f'  [FAIL] AST 语法: {err}')
            total_fail += 1

        # 2. 括号匹配
        ok, err = check_brackets(fp)
        if ok:
            print(f'  [OK] 括号匹配')
            total_ok += 1
        else:
            print(f'  [FAIL] 括号匹配: {err}')
            total_fail += 1

        # 3. 硬编码路径
        ok, issues = check_hardcoded_paths(fp)
        if ok:
            print(f'  [OK] 无硬编码路径')
            total_ok += 1
        else:
            for iss in issues:
                print(f'  [WARN] 硬编码路径: {iss}')
            total_ok += 1  # 路径问题算警告

        # 4. 导入路径
        ok, issues = check_import_paths(fp)
        if ok:
            print(f'  [OK] 导入路径')
            total_ok += 1
        else:
            for iss in issues:
                print(f'  [WARN] 导入路径: {iss}')
            total_ok += 1

        print()

    # 前端文件
    print('--- 前端文件 ---')
    frontend = [
        ('dispatch_center.html', BASE / 'templates' / 'dispatch_center.html'),
        ('dispatch_center.js', BASE / 'static' / 'js' / 'dispatch_center.js'),
        ('dispatch_center.css', BASE / 'static' / 'css' / 'dispatch_center.css'),
    ]
    for name, fp in frontend:
        if not fp.exists():
            print(f'  SKIP  {name} (文件不存在)')
            continue
        ok, err = check_brackets(fp)
        if ok:
            print(f'  [OK] {name} 括号匹配')
            total_ok += 1
        else:
            print(f'  [FAIL] {name} 括号匹配: {err}')
            total_fail += 1

    print()
    print('=' * 60)
    print(f'  汇总: 通过 {total_ok}  |  失败 {total_fail}')
    print('=' * 60)

    return 0 if total_fail == 0 else 1

if __name__ == '__main__':
    sys.exit(main())