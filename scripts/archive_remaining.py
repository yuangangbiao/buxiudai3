"""补移遗漏: 6 个 .js (在 .browser_test) + 1 个名字写错的 .py"""
import shutil
from pathlib import Path

ARCHIVE = Path(r'D:\yuan\不锈钢网带跟单3.0\scripts\_diagnostics_2026_06_12')

# 1. .js 浏览器测试脚本 (在 .browser_test)
JS_FILES = [
    'trace_errors.js',
    'dump_buttons.js',
    'shot_dashboard.js',
    'verify_no_errors.js',
    'shot_shortage.js',
    'fix_物料详情_滚到底.png',  # 截图也算诊断输出, 一起归档
]
JS_SRC = Path(r'D:\yuan\不锈钢网带跟单3.0\.browser_test')

# 2. 名字写错的 py
PY_FIX = {
    'check_5008_dashboard.py': 'check_5008_dashboard.py',  # 实际叫这个名字
}
PY_SRC = Path(r'D:\yuan\不锈钢网带跟单3.0\scripts')

print('补移 .js + 图片 (从 .browser_test):')
moved = 0
for fn in JS_FILES:
    src = JS_SRC / fn
    if src.exists():
        dst = ARCHIVE / fn
        shutil.move(str(src), str(dst))
        print(f'  ✓ {fn}')
        moved += 1
    else:
        print(f'  ? {fn} (不在 .browser_test)')

print('\n补移 .py (名字修正):')
for fn in PY_FIX.values():
    src = PY_SRC / fn
    if src.exists():
        dst = ARCHIVE / fn
        shutil.move(str(src), str(dst))
        print(f'  ✓ {fn}')
        moved += 1
    else:
        print(f'  ? {fn} (不在 scripts/)')

# 顺手归档 archive_diagnostics.py 自己 (它也是诊断脚本)
self_path = PY_SRC / 'archive_diagnostics.py'
if self_path.exists():
    shutil.move(str(self_path), ARCHIVE / 'archive_diagnostics.py')
    print('  ✓ archive_diagnostics.py (自身)')
    moved += 1

print(f'\n补移共 {moved} 个文件')

# 最终验证
print('\n[最终验证]')
print(f'  scripts/ 根目录文件数: {len([f for f in PY_SRC.iterdir() if f.is_file()])}')
print(f'  .browser_test/ 文件数: {len([f for f in JS_SRC.iterdir() if f.is_file()])}')
print(f'  _diagnostics_2026_06_12/ 文件数: {len([f for f in ARCHIVE.iterdir() if f.is_file()])}')
