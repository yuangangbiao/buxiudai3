# -*- coding: utf-8 -*-
"""检查 _core.py 状态"""
import os
import subprocess

os.chdir(r'd:\yuan\不锈钢网带跟单3.0')

# 当前 _core.py
with open('mobile_api_ai/dispatch_center/_core.py', 'rb') as f:
    content = f.read()
print(f'当前 _core.py: {content.count(b"\n")} 行 (按 LF 计)')
print(f'当前 _core.py: {len(content)} bytes')

# HEAD _core.py via git show
r = subprocess.run(['git', 'show', 'HEAD:./mobile_api_ai/dispatch_center/_core.py'],
                   capture_output=True)
print(f'HEAD _core.py via git show: {r.stdout.count(b"\\n") if r.returncode == 0 else "ERROR"} 行')
print(f'git show returncode: {r.returncode}')
if r.returncode != 0:
    print(f'git show stderr: {r.stderr.decode("utf-8", errors="replace")[:500]}')

# git show stdout 保存
if r.returncode == 0:
    with open('scripts/tools/.head_core.py', 'wb') as f:
        f.write(r.stdout)
    print(f'已保存 HEAD version 到 .head_core.py ({len(r.stdout)} bytes)')