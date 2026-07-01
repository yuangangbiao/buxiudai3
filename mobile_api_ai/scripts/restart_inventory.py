# -*- coding: utf-8 -*-
"""杀掉监听 5010 端口的进程，让 IDE 看护自动重启以加载新 .env"""
import subprocess
import time

# 用 netstat + taskkill
out = subprocess.run(['netstat', '-ano', '-p', 'TCP'], capture_output=True, text=True, shell=True).stdout
killed = []
for line in out.splitlines():
    if ':5010' in line and ('LISTENING' in line or 'ESTABLISHED' in line):
        parts = line.strip().split()
        if parts and parts[-1].isdigit():
            pid = int(parts[-1])
            if pid in killed:
                continue
            r = subprocess.run(['taskkill', '/F', '/PID', str(pid)],
                               capture_output=True, text=True, shell=True)
            killed.append(pid)
            print(f'Killed PID {pid}: {r.stdout.strip() or r.stderr.strip()}')

if not killed:
    print('No process found on port 5010')
else:
    print('Waiting 3s for IDE to respawn...')
    time.sleep(3)
