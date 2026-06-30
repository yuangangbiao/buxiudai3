# -*- coding: utf-8 -*-
"""修复_migrate_tables函数中的所有缩进问题"""

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
    elif in_migrate and line.strip() and line.strip().startswith('def ') and i > start_line + 1:
        end_line = i
        in_migrate = False

if end_line is None:
    end_line = len(lines)

# 修复缩进：移除一个缩进级别（4个空格）
fixed_lines = []
for i, line in enumerate(lines):
    if start_line < i < end_line:
        # 如果行有多余的缩进，减少4个空格
        if line.startswith('        '):  # 8个空格
            fixed_lines.append(line[4:])  # 减少到4个空格
        elif line.startswith('    '):  # 4个空格（已经正确）
            fixed_lines.append(line)
        elif line.strip() == '':  # 空行
            fixed_lines.append(line)
        elif line.strip().startswith('#'):  # 注释
            if line.startswith('        '):
                fixed_lines.append(line[4:])
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)
    else:
        fixed_lines.append(line)

with open('models/database.py', 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print('缩进修复完成')
