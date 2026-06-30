import subprocess
import sys
import os

PYTHON = r"C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\python.exe"
script = r"d:\yuan\不锈钢网带跟单3.0\start_servers.py"

result = subprocess.Popen(
    [PYTHON, script],
    cwd=r"d:\yuan\不锈钢网带跟单3.0",
    creationflags=subprocess.CREATE_NEW_CONSOLE
)
print(f"Started with PID: {result.pid}")
