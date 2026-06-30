# -*- coding: utf-8 -*-
"""完全移除SQLite分支代码"""

with open('models/database.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 状态变量
in_else_block = False
else_block_start = 0
if_block_indent = 0

result_lines = []

i = 0
while i < len(lines):
    line = lines[i]
    
    # 检测是否进入SQLite的else块
    if line.strip() == 'else:' and i > 0:
        # 检查前面是否是mysql的if块结束
        j = i - 1
        while j >= 0 and lines[j].strip() == '':
            j -= 1
        if j >= 0 and lines[j].strip().endswith('""")'):
            in_else_block = True
            else_block_start = i
            # 记录if块的缩进级别
            k = j - 1
            while k >= 0 and (lines[k].strip() == '' or lines[k].strip().startswith('#')):
                k -= 1
            if k >= 0 and 'if current_db_type' in lines[k]:
                if_block_indent = len(lines[k]) - len(lines[k].lstrip())
            continue
    
    # 如果在else块中，找到块的结束
    if in_else_block:
        current_indent = len(line) - len(line.lstrip())
        # 当缩进回到if块级别且不是空行或注释时，说明else块结束
        if line.strip() != '' and not line.strip().startswith('#') and current_indent <= if_block_indent:
            in_else_block = False
        else:
            i += 1
            continue
    
    # 移除 if current_db_type == "mysql": 语句
    if 'if current_db_type == "mysql":' in line:
        i += 1
        # 跳过空行
        while i < len(lines) and lines[i].strip() == '':
            i += 1
        continue
    
    result_lines.append(line)
    i += 1

# 写入文件
with open('models/database.py', 'w', encoding='utf-8') as f:
    f.writelines(result_lines)

print('SQLite分支已移除')
