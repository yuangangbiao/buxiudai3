"""
批量修复 request.get_json(force=True, ...) -> request.get_json(...)

替换规则:
  get_json(force=True, silent=True) -> get_json(silent=True)
  get_json(force=True)               -> get_json()
"""
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 两种需要替换的模式
PATTERNS = [
    (re.compile(r'get_json\(force=True,\s*silent=True\)'), 'get_json(silent=True)'),
    (re.compile(r'get_json\(force=True\)'),               'get_json()'),
]

EXCLUDE_DIRS = {'.git', '__pycache__', 'node_modules', 'venv', '.venv', 'deploy_prepared', 'dist', 'build'}
# 云端专用文件，禁止本地修改
EXCLUDE_FILES = {'wechat_server.py', 'wechat_cloud.py', 'fix_get_json.py'}

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Count matches before replacement
    count_before = 0
    for pattern, _ in PATTERNS:
        count_before += len(pattern.findall(content))

    original = content
    for pattern, replacement in PATTERNS:
        content = pattern.sub(replacement, content)

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, count_before
    return False, 0


def main():
    fixed_files = []
    total_replacements = 0

    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in files:
            if f.endswith('.py') and f not in EXCLUDE_FILES:
                filepath = os.path.join(root, f)
                fixed, count = fix_file(filepath)
                if fixed:
                    fixed_files.append((os.path.relpath(filepath, BASE_DIR), count))
                    total_replacements += count

    print(f"\n已修复 {len(fixed_files)} 个文件，共 {total_replacements} 处替换:")
    for rel, count in fixed_files:
        print(f"  {rel} ({count} 处)")


if __name__ == '__main__':
    main()
