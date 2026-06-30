import subprocess
import sys
import os

PYTHON = r"C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\python.exe"
script = r"d:\yuan\不锈钢网带跟单3.0\direct_start.py"

# 启动子进程
proc = subprocess.Popen(
    [PYTHON, script],
    cwd=r"d:\yuan\不锈钢网带跟单3.0",
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)

# 实时输出
try:
    while proc.poll() is None:
        line = proc.stdout.readline()
        if line:
            print(line, end='')
except KeyboardInterrupt:
    print("\n[中断] 正在关闭...")
    proc.terminate()
    proc.wait()
