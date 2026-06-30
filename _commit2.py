import subprocess, os

WORK_DIR = r'd:\yuan\不锈钢网带跟单3.0'
SSH_KEY = r'C:\Users\lenovo\.ssh\id_rsa_github'
env = os.environ.copy()
env['GIT_SSH_COMMAND'] = f'ssh -i "{SSH_KEY}" -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL'
env['PYTHONIOENCODING'] = 'utf-8'
os.chdir(WORK_DIR)

r = subprocess.run(['git', 'add', '-A'], capture_output=True, text=True, encoding='utf-8', errors='replace')
r = subprocess.run(['git', 'status', '--short'], capture_output=True, text=True, encoding='utf-8', errors='replace')
changed = [l for l in r.stdout.splitlines() if l.strip()]
print(f'变更: {len(changed)} 个')
for l in changed[:10]: print(f'  {l}')

r = subprocess.run(['git', 'commit', '-m',
    'chore: remove 44 dead docs directories (v3.7.x/v3.8.x + old project dirs)'],
    capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
print(f'commit: {"ok" if r.returncode == 0 else r.stderr[:100]}')

r = subprocess.run(['git', 'push', 'github', 'master'],
    capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
print(f'push: {"ok" if r.returncode == 0 else r.stderr[:100]}')
