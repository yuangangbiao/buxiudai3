import subprocess, os

WORK_DIR = r'd:\yuan\不锈钢网带跟单3.0'
SSH_KEY = r'C:\Users\lenovo\.ssh\id_rsa_github'
env = os.environ.copy()
env['GIT_SSH_COMMAND'] = f'ssh -i "{SSH_KEY}" -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL'
env['PYTHONIOENCODING'] = 'utf-8'
os.chdir(WORK_DIR)

r = subprocess.run(['git', 'add',
    'mobile_api_ai/scripts/tools/cleanup_dirty_completed_qty.py',
    '_commit_update.py'],
    capture_output=True, text=True, encoding='utf-8', errors='replace')
r = subprocess.run(['git', 'status', '--short'],
    capture_output=True, text=True, encoding='utf-8', errors='replace')
print(f'status: {r.stdout[:200]}')
r = subprocess.run(['git', 'commit', '-m',
    'fix(scripts): BUG-P0-003 cleanup - target process_records not data_packages'],
    capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
print(f'commit: {"ok" if r.returncode == 0 else r.stderr[:100]}')
r = subprocess.run(['git', 'push', 'github', 'master'],
    capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
print(f'push: {"ok" if r.returncode == 0 else r.stderr[:100]}')
