# -*- coding: utf-8 -*-
import subprocess, sys
code = 'import ast; ast.parse(open(r"d:\\\\yuan\\\\不锈钢网带跟单3.0\\\\mobile_api_ai\\\\dispatch_center\\\\_core.py").read())'
result = subprocess.run(
    [sys.executable, '-c', code],
    capture_output=True, text=True
)
print(f"Exit code: {result.returncode}")
print(f"stderr: {result.stderr[:800]}")
