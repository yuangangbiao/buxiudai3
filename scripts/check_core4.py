"""[调试 v4]"""
import subprocess

for commit in ['HEAD', '24946517', '5dd18eb4', '4f3e5f9a', '2599c47d', '9a4e5c7b']:
    r = subprocess.run(['git', 'show', f'{commit}:./mobile_api_ai/dispatch_center/_core.py'],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f'{commit}: ERROR')
        continue
    has = '_persist_thread' in r.stdout
    print(f'{commit} _persist_thread: {has}')

with open(r'mobile_api_ai\dispatch_center\_core.py', 'r', encoding='utf-8') as f:
    content = f.read()
print('working tree _persist_thread:', '_persist_thread' in content)
print('working tree is_alive check:', 'is_alive' in content)