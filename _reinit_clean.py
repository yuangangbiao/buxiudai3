import subprocess
import os
import shutil

WORK_DIR = r'd:\yuan\不锈钢网带跟单3.0'
os.chdir(WORK_DIR)

# 1. 备份 git remote
result = subprocess.run(['git', 'remote', '-v'], capture_output=True, text=True, encoding='utf-8', errors='replace')
remote_github = ''
for line in result.stdout.splitlines():
    if 'github' in line and '(push)' in line:
        remote_github = line.split()[1]
        break
print(f'Remote: {remote_github}')

# 2. 删除 .git
shutil.rmtree('.git')
print('.git 已删除')

# 3. git init
subprocess.run(['git', 'init'], capture_output=True, encoding='utf-8', errors='replace')
subprocess.run(['git', 'checkout', '-b', 'master'], capture_output=True, encoding='utf-8', errors='replace')
subprocess.run(['git', 'remote', 'add', 'github', remote_github], capture_output=True, encoding='utf-8', errors='replace')
print('git 重新初始化')

# 4. 收集文件
SKIP_DIRS = {'build', 'build_dashboard_launcher', 'build_dashboard_new',
             'build_license_temp', 'build_with_license_temp',
             'final_inventory_build', 'temp_inventory_build',
             'visualization_app', '__pycache__', '.pytest_cache',
             'node_modules', '.mypy_cache', '.git'}
SKIP_FILES = {'_src.tar', '_push_api.py', '_push_gh.py', '_push_gh_proxy.py',
              '_push_ssh.py', '_push_ssh_final.py', '_push_via_api.py',
              '_push_gitcode.py', '_test_ssh.py', '_reinit_git.py',
              '_reinit_git2.py', '_reinit_git3.py', '_rebuild_git.py',
              '_remove_build.py', '_remove_build2.py', '_filter_repo.py',
              '_check_token.py', '_find_bigfile.py', '_find_unreachable.py',
              '_check_token.ps1', '_login_gh.ps1', '_create_repo.py',
              '_test_pool.py', '_test_cursor.py'}

all_files = []
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('.')]
    rel = os.path.relpath(root, '.')
    if rel == '.': rel = ''
    for f in files:
        if f in SKIP_FILES or f.startswith('.') or f.endswith('.pyc') or f.endswith('.pyo'):
            continue
        fp = os.path.join(root, f)
        # 跳过 build 目录
        if any(s in fp for s in ['build_dashboard', 'build_license',
                                   'build_with_license', 'final_inventory_build',
                                   'temp_inventory_build', 'visualization_app']):
            continue
        f_rel = os.path.join(rel, f).replace(os.sep, '/').lstrip('/')
        if not f_rel:
            continue
        if os.path.exists(fp) and os.path.isfile(fp):
            size = os.path.getsize(fp)
            if size > 100 * 1024 * 1024:
                print(f'  跳过超大文件: {f_rel} ({size//1024//1024}MB)')
                continue
            all_files.append(fp)

print(f'收集了 {len(all_files)} 个文件')

# 5. 逐个添加
added = 0
for f in all_files:
    subprocess.run(['git', 'add', '--', f], capture_output=True, encoding='utf-8', errors='replace')
    added += 1

print(f'已添加 {added} 个文件')

# 6. 提交
subprocess.run(['git', 'config', 'user.email', 'yuangangbiao@github.com'], capture_output=True, encoding='utf-8', errors='replace')
subprocess.run(['git', 'config', 'user.name', 'yuangangbiao'], capture_output=True, encoding='utf-8', errors='replace')
result = subprocess.run(['git', 'commit', '-m', '不锈钢网带跟单系统 v3.7.1 - 初始化提交'],
    capture_output=True, text=True, encoding='utf-8', errors='replace')
if result.returncode == 0:
    print('提交成功!')
else:
    print(f'提交失败: {result.stderr[:200]}')
