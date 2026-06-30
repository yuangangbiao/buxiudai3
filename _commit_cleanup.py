import subprocess, os

WORK_DIR = r'd:\yuan\不锈钢网带跟单3.0'
SSH_KEY = r'C:\Users\lenovo\.ssh\id_rsa_github'
env = os.environ.copy()
env['GIT_SSH_COMMAND'] = f'ssh -i "{SSH_KEY}" -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL'
env['PYTHONIOENCODING'] = 'utf-8'
os.chdir(WORK_DIR)

r = subprocess.run(['git', 'status', '--short'], capture_output=True, text=True, encoding='utf-8', errors='replace')
changed = [l for l in r.stdout.splitlines() if l.strip()]
print(f'变更: {len(changed)} 个')

r = subprocess.run(['git', 'add', '-A'], capture_output=True, text=True, encoding='utf-8', errors='replace')
r = subprocess.run(['git', 'commit', '-m',
    'chore: remove dead files (138 items)\n\n'
    'scripts/archive/ - 4 verify scripts\n'
    'scripts/build/ - 2 exe builders\n'
    'scripts/debug/ - 6 test scripts\n'
    'scripts/tools/ - 86 temp files (.txt/_/cleanup/test_/verify_/publish_)\n'
    'tests/reports/logs/ - 39 pytest logs\n'
    'tests/reports/*.xml - old baseline\n'
    'tests/**/*.bak - 4 backup files\n'
    'docs/v3.6.8/ - 20 old docs\n'
    'docs/v3.7.0/ - 7 old docs (keep TODO_v3.7.1.md)\n'
    'docs/24 old project directories'],
    capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
print(f'commit: {"ok" if r.returncode == 0 else r.stderr[:100]}')

r = subprocess.run(['git', 'push', 'github', 'master'],
    capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
print(f'push: {"ok" if r.returncode == 0 else r.stderr[:100]}')
