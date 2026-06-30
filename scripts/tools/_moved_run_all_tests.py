#!/usr/bin/env python
"""Run all unit and integration tests, print summary."""
import subprocess
import sys

result = subprocess.run(
    [sys.executable, '-m', 'pytest', 'tests/unit/', 'tests/integration/', '-v', '--tb=line'],
    capture_output=True, text=True, cwd=r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai',
    timeout=120
)
outpath = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\tests\test_full_output.txt'
with open(outpath, 'w', encoding='utf-8') as f:
    f.write(result.stdout[-5000:])
    if result.stderr:
        f.write("\n\nSTDERR:\n" + result.stderr[-2000:])
    f.write(f"\n\nExit code: {result.returncode}")
print(f"Output written to {outpath}")
sys.exit(result.returncode)
