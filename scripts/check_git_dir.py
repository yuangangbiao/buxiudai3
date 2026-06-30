"""[debug] 检查 git dir"""
import subprocess
import os

r = subprocess.run(['git', 'rev-parse', '--git-dir'], capture_output=True, text=True)
print('GIT_DIR:', r.stdout.strip())

r = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True)
print('TOPLEVEL:', r.stdout.strip())

# .git 是 file 还是 dir
git_path = os.path.join('d:/yuan/不锈钢网带跟单3.0', '.git')
print('.git 存在:', os.path.exists(git_path))
if os.path.exists(git_path):
    print('.git 是文件:', os.path.isfile(git_path))
    print('.git 是目录:', os.path.isdir(git_path))

    if os.path.isfile(git_path):
        with open(git_path, 'r') as f:
            content = f.read()
        print('.git 文件内容:', content[:200])

# 看 D:/yuan/.git
d_yuan_git = 'D:/yuan/.git'
print('D:/yuan/.git 存在:', os.path.exists(d_yuan_git))
if os.path.exists(d_yuan_git):
    print('D:/yuan/.git 是目录:', os.path.isdir(d_yuan_git))