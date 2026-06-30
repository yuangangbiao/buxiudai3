import subprocess, os

WORK_DIR = r'd:\yuan\不锈钢网带跟单3.0'
SSH_KEY = r'C:\Users\lenovo\.ssh\id_rsa_github'
env = os.environ.copy()
env['GIT_SSH_COMMAND'] = f'ssh -i "{SSH_KEY}" -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL'
env['PYTHONIOENCODING'] = 'utf-8'
os.chdir(WORK_DIR)

f = '_rm_temp.py'
fp = os.path.join(WORK_DIR, f)
if os.path.exists(fp):
    os.remove(fp)
    print(f'removed {f}')

r = subprocess.run(['git', 'add', '-A'], capture_output=True, text=True, encoding='utf-8', errors='replace')
r = subprocess.run(['git', 'status'], capture_output=True, text=True, encoding='utf-8', errors='replace')
print(r.stdout[:300])
r = subprocess.run(['git', 'commit', '-m', 'chore: remove temp file'],
    capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
print(f'commit: {"ok" if r.returncode == 0 else r.stderr[:100]}')
r = subprocess.run(['git', 'push', 'github', 'master'],
    capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
print(f'push: {"ok" if r.returncode == 0 else r.stderr[:100]}')
