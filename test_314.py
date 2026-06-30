# -*- coding: utf-8 -*-
import subprocess, sys, os

test_code = '''"""test\u4e2d\u6587\uff0ctest"""
x = 1'''

result = subprocess.run(
    [sys.executable, '-c', 'import ast; ast.parse("""' + test_code + '""")'],
    capture_output=True, text=True
)
print(f"Python {sys.version}")
print(f"Exit: {result.returncode}")
print(f"Stderr: {result.stderr}")

result2 = subprocess.run(
    [sys.executable, '-c',
     f'import ast; code = """test\\uff0ctest"""; ast.parse(code)'],
    capture_output=True, text=True
)
print(f"\nDirect parse exit: {result2.returncode}, stderr: {result2.stderr[:200]}")
