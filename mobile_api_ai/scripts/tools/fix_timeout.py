"""批量替换Python文件中的硬编码timeout为环境变量模式"""
import re
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXCLUDE_DIRS = {'云端更新包', '云端更新包_v1.0', '云端更新包_v1.1', '__pycache__', '.git', 'scripts', 'node_modules'}

TIMEOUT_MAP = {
    30:  ('REQUEST_TIMEOUT_EXTRA', '30'),
    15:  ('REQUEST_TIMEOUT_LONG', '15'),
    10:  ('REQUEST_TIMEOUT_NORMAL', '10'),
    5:   ('REQUEST_TIMEOUT_FAST', '5'),
    3:   ('REQUEST_TIMEOUT_QUICK', '3'),
    2:   ('REQUEST_TIMEOUT_QUICK', '2'),
}

SOCKET_TIMEOUT_DEFAULT = ('SOCKET_CONNECT_TIMEOUT', '5')

def needs_os_import(content):
    return 'os.environ' in content or 'os.getenv' in content

def add_os_import_if_needed(content, filepath):
    if not needs_os_import(content):
        return content
    lines = content.split('\n')
    has_os_import = any(re.match(r'^import\s+os\b', l) or re.match(r'^from\s+os\b', l) for l in lines)
    if has_os_import:
        return content
    import_line_idx = -1
    for i, l in enumerate(lines):
        if re.match(r'^import\s', l):
            import_line_idx = i
            break
    if import_line_idx >= 0:
        lines.insert(import_line_idx, 'import os')
    else:
        lines.insert(0, 'import os')
    return '\n'.join(lines)

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    original = content
    socket_pattern = re.compile(r'socket_connect_timeout=(\d+)')
    socket_replacement = f'socket_connect_timeout=int(os.environ.get(\'{SOCKET_TIMEOUT_DEFAULT[0]}\', \'{SOCKET_TIMEOUT_DEFAULT[1]}\'))'
    content = socket_pattern.sub(socket_replacement, content)
    for timeout_val, (env_name, default) in TIMEOUT_MAP.items():
        pattern = re.compile(r'(?<!os\.environ\.get\(\')timeout=' + str(timeout_val) + r'(?!\')')
        replacement = f'timeout=int(os.environ.get(\'{env_name}\', \'{default}\'))'
        content = pattern.sub(replacement, content)
    if content != original:
        content = add_os_import_if_needed(content, filepath)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    changed = []
    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in files:
            if not f.endswith('.py'):
                continue
            if f.endswith('.bak.py'):
                continue
            filepath = os.path.join(root, f)
            if fix_file(filepath):
                relpath = os.path.relpath(filepath, BASE_DIR)
                changed.append(relpath)
                print(f'  MODIFIED: {relpath}')
    print(f'\nTotal: {len(changed)} files modified')

if __name__ == '__main__':
    main()
