"""T7: 将根目录的散乱 debug/test 文件移至 scripts/archive/"""
import os, shutil, subprocess, sys

base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
archive = os.path.join(base, 'scripts', 'archive')
os.makedirs(archive, exist_ok=True)

files = [
    # debug_* files
    'debug_analyze.py', 'debug_compare.py', 'debug_compare2.py',
    'debug_compare3.py', 'debug_compare4.py', 'debug_fields.py',
    'debug_reports.py', 'debug_reports2.py',
    # __tmp* and __verify* files
    '__tmp_api_test.py', '__tmp_validate.py',
    '__verify_step1.py', '__verify_step2.py', '__verify_step3.py', '__verify_step4.py',
    # _ standalone scripts
    '_kill2.py', '_temp_check_cs.py', '_wait_build.py',
    '_verify2.py', '_verify_exe.py', '_verify_final.py',
]

moved = 0
for f in files:
    src = os.path.join(base, f)
    dst = os.path.join(archive, f)
    if os.path.exists(src):
        shutil.move(src, dst)
        moved += 1
        print(f'[MOVED] {f}')

print(f'\nDone. Moved {moved} files to scripts/archive/')
