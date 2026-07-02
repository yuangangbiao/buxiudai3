# -*- coding: utf-8 -*-
import os, sys
ROOT = r'd:\yuan\不锈钢网带跟单3.0'
nul_count = 0
errors = []
# 自底向上遍历
for root, dirs, files in os.walk(ROOT):
    if 'archive' in root or '.git' in root or '__pycache__' in root:
        continue
    for f in files:
        if f == 'nul' or f.lower() == 'nul':
            path = os.path.join(root, f)
            try:
                os.remove(path)
                nul_count += 1
            except PermissionError:
                # 尝试用 Windows API 强制删除
                try:
                    os.system(f'del /f /q "{path}" 2>nul')
                    nul_count += 1
                except Exception as e:
                    errors.append((path, str(e)))
            except Exception as e:
                errors.append((path, str(e)))
print(f'已删除 {nul_count} 个 nul 文件')
if errors:
    print(f'错误 {len(errors)} 个:')
    for p, e in errors[:5]:
        print(f'  {p}: {e}')
