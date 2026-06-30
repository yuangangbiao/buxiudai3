"""[调试 v5]"""
import subprocess

# backup 分支 log
r = subprocess.run(['git', 'log', 'backup-before-resplit', '-3', '--oneline'], capture_output=True, text=True)
print('backup 分支:')
print(r.stdout)
print()

# backup 分支 _core.py
r2 = subprocess.run(['git', 'show', 'backup-before-resplit:./mobile_api_ai/dispatch_center/_core.py'],
                    capture_output=True, text=True)
has = '_persist_thread' in r2.stdout
print('backup 分支 _persist_thread:', has)

# 看 backup vs 2599c47d 在 _core.py 的 diff
r3 = subprocess.run(['git', 'diff', 'backup-before-resplit', '2599c47d', '--stat', '--', './mobile_api_ai/dispatch_center/_core.py'],
                    capture_output=True, text=True)
print('backup vs 2599c47d:')
print(r3.stdout[:300])

# 看 _core.py 是否在 backup 的 commits 中被修改
r4 = subprocess.run(['git', 'log', 'backup-before-resplit', '--oneline', '--', './mobile_api_ai/dispatch_center/_core.py'],
                    capture_output=True, text=True)
print('_core.py 在 backup 分支的 commits:')
print(r4.stdout)