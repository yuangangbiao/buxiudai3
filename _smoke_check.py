import subprocess, sys, os
os.chdir(r'd:\yuan\不锈钢网带跟单3.0')
r = subprocess.run([sys.executable, '-m', 'pytest', 'tests/L1_smoke/', '--tb=short', '-q'],
    capture_output=True, text=True, encoding='utf-8', errors='replace')
import re
m = re.search(r'(\d+) passed', r.stdout)
passed = int(m.group(1)) if m else 0
m2 = re.search(r'(\d+) failed', r.stdout)
failed = int(m2.group(1)) if m2 else 0
print(f'L1 smoke: {passed} passed / {failed} failed')
print(f'返回码: {r.returncode}')
