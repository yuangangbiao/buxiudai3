"""[调试] 检查 _core.py 的状态"""
import subprocess

for commit in ['HEAD', '24946517', '5dd18eb4', '4f3e5f9a', '2599c47d', '9a4e5c7b']:
    r = subprocess.run(['git', 'show', f'{commit}:mobile_api_ai/dispatch_center/_core.py'],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f'{commit}: ERROR {r.stderr[:100]}')
        continue
    has = '_persist_thread' in r.stdout
    print(f'{commit} _core.py 中 _persist_thread: {has}')