# -*- coding: utf-8 -*-
"""修复_migrate_tables函数中的缩进问题"""

with open('models/database.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到_migrate_tables函数的范围
start_line = None
end_line = None
in_migrate = False
indent_level = 0

for i, line in enumerate(lines):
    if 'def _migrate_tables' in line:
        start_line = i
        in_migrate = True
        indent_level = len(line) - len(line.lstrip())
    elif in_migrate and line.strip() and not line.strip().startswith('#') and len(line) - len(line.lstrip()) <= indent_level and i > start_line + 1:
        end_line = i
        in_migrate = False

if end_line is None:
    end_line = len(lines)

# 修复_migrate_tables函数中的缩进
fixed_lines = []
for i, line in enumerate(lines):
    if start_line < i < end_line:
        # 如果行有缩进，减少一个缩进级别
        stripped = line.lstrip()
        if stripped and not stripped.startswith('#'):
            # 减少8个空格（一个缩进级别）
            if line.startswith('        '):
                fixed_lines.append(line[4:])  # 减少4个空格
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)
    else:
        fixed_lines.append(line)

with open('models/database.py', 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print('缩进修复完成')
