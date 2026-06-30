"""启动 5002 后台进程"""
import subprocess
import sys
import time

# 启动 5002
proc = subprocess.Popen(
    [sys.executable, r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\container_center_api.py'],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    cwd=r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai',
    text=True,
)

# 写 PID
with open(r'D:\yuan\不锈钢网带跟单3.0\5002.pid', 'w') as f:
    f.write(str(proc.pid))

print(f'Started 5002 as PID {proc.pid}')

# 启动后立即返回（不阻塞）
# 监听 8 秒
import threading

def read_output():
    try:
        for line in proc.stdout:
            print(line, end='')
    except Exception as e:
        print(f'Output read error: {e}')

t = threading.Thread(target=read_output, daemon=True)
t.start()

time.sleep(10)

# 写日志
import os
log_path = r'D:\yuan\不锈钢网带跟单3.0\5002.log'
with open(log_path, 'a', encoding='utf-8') as f:
    f.write(f'\n=== {time.strftime("%Y-%m-%d %H:%M:%S")} 启动尝试 ===\n')

print(f'Process running: {proc.poll() is None}')
print(f'PID: {proc.pid}')

# 持续运行
try:
    proc.wait()
except KeyboardInterrupt:
    proc.terminate()
