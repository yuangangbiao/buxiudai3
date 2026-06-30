import subprocess, os

WORK_DIR = r'd:\yuan\不锈钢网带跟单3.0'
SSH_KEY = r'C:\Users\lenovo\.ssh\id_rsa_github'
env = os.environ.copy()
env['GIT_SSH_COMMAND'] = f'ssh -i "{SSH_KEY}" -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL'
env['PYTHONIOENCODING'] = 'utf-8'
os.chdir(WORK_DIR)

# 删除本地临时文件
for f in ['_cleanup2.py', '_commit2.py']:
    fp = os.path.join(WORK_DIR, f)
    if os.path.exists(fp):
        os.remove(fp)
        print(f'删除本地 {f}')

# 从 git 中移除（已提交的）
r = subprocess.run(['git', 'rm', '-f', '_cleanup2.py', '_commit2.py'],
    capture_output=True, text=True, encoding='utf-8', errors='replace')
print(f'git rm: {r.returncode}')

# 恢复 TODO_v3.7.1.md（如果它在 docs/ 根目录）
todo_path = os.path.join(WORK_DIR, 'docs', 'TODO_v3.7.1.md')
if not os.path.exists(todo_path):
    print('TODO_v3.7.1.md 不存在，检查是否在 v3.7.0/ 里被删了')
else:
    print('TODO_v3.7.1.md 存在')

r = subprocess.run(['git', 'add', '-A'], capture_output=True, text=True, encoding='utf-8', errors='replace')
r = subprocess.run(['git', 'commit', '-m', 'fix: remove committed temp files (_cleanup2.py _commit2.py)'],
    capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
print(f'commit: {"ok" if r.returncode == 0 else r.stderr[:100]}')

r = subprocess.run(['git', 'push', 'github', 'master'],
    capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
print(f'push: {"ok" if r.returncode == 0 else r.stderr[:100]}')
