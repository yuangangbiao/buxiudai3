import subprocess, os

WORK_DIR = r'd:\yuan\不锈钢网带跟单3.0'
SSH_KEY = r'C:\Users\lenovo\.ssh\id_rsa_github'
env = {**os.environ, 'GIT_SSH_COMMAND': f'ssh -i "{SSH_KEY}" -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL'}

os.chdir(WORK_DIR)

# 查看主仓库最新提交
r = subprocess.run(['git', 'log', '-1', '--format=%H %s'],
    capture_output=True, text=True, encoding='utf-8', errors='replace')
print(f'本地 HEAD: {r.stdout.strip()}')

# 查看 GitHub 最新提交
r = subprocess.run(['git', 'fetch', 'github', 'master'],
    capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
print(f'fetch: {r.returncode}')

r = subprocess.run(['git', 'log', '-1', '--format=%H %s', 'github/master'],
    capture_output=True, text=True, encoding='utf-8', errors='replace')
print(f'GitHub HEAD: {r.stdout.strip() or "(无)"}')

# 对比
r = subprocess.run(['git', 'merge-base', 'HEAD', 'github/master'],
    capture_output=True, text=True, encoding='utf-8', errors='replace')
common = r.stdout.strip()
print(f'共同祖先: {common}')

r = subprocess.run(['git', 'log', '--oneline', f'{common}..HEAD'],
    capture_output=True, text=True, encoding='utf-8', errors='replace')
print(f'本地新提交: {r.stdout or "(无)"}')

r = subprocess.run(['git', 'log', '--oneline', f'{common}..github/master'],
    capture_output=True, text=True, encoding='utf-8', errors='replace')
print(f'GitHub新提交: {r.stdout or "(无)"}')

# 如果 GitHub 没有真正的新内容（只是同步），直接 force push
r = subprocess.run(['git', 'push', 'github', 'master', '--force'],
    capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
print(f'\nforce push: {"成功" if r.returncode == 0 else r.stderr[:200]}')
