# -*- coding: utf-8 -*-
import subprocess, sys

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/unit",
     "--ignore=tests/unit/core/test_app.py",
     "--tb=no", "--no-cov", "-q"],
    capture_output=True, text=True,
    cwd=r"d:\yuan\不锈钢网带跟单3.0",
    timeout=300
)
output = result.stdout + result.stderr
print(output[-5000:] if len(output) > 5000 else output)
with open(r"d:\yuan\不锈钢网带跟单3.0\tests\logs\pytest_unit_all.txt", "w", encoding="utf-8") as f:
    f.write(output)
print("\nExit code:", result.returncode)
