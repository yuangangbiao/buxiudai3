"""[调试 v3] 用绝对路径"""
import subprocess

for commit in ['HEAD', '24946517', '5dd18eb4', '4f3e5f9a', '2599c47d', '9a4e5c7b']:
    path = 'mobile_api_ai/dispatch_center/_core.py'
    r = subprocess.run(['git', 'show', f'{commit}:{path}'], capture_output=True, text=True)
    if r.returncode != 0:
        print(f'{commit}: ERROR')
        continue
    has = '_persist_thread' in r.stdout
    print(f'{commit} _persist_thread: {has}')