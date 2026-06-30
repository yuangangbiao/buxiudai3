"""运行 E2E 测试并输出结果到文件"""
import sys
import os
sys.path.insert(0, r'd:\yuan\不锈钢网带跟单3.0')
os.chdir(r'd:\yuan\不锈钢网带跟单3.0')

import subprocess
result = subprocess.run(
    ['python', 'scripts/e2e_publish_test.py'],
    capture_output=True,
    text=True,
    cwd=r'd:\yuan\不锈钢网带跟单3.0'
)
print("STDOUT:")
print(result.stdout)
print("STDERR:")
print(result.stderr)
print("EXIT CODE:", result.returncode)
