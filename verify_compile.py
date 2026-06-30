# -*- coding: utf-8 -*-
import subprocess, sys
result = subprocess.run(
    [sys.executable, '-m', 'py_compile',
     r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\dispatch_center\_core.py'],
    capture_output=True, text=True
)
print(f"Exit code: {result.returncode}")
if result.stdout:
    print(f"stdout: {result.stdout}")
if result.stderr:
    print(f"stderr: {result.stderr}")
