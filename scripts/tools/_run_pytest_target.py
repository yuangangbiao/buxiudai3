# -*- coding: utf-8 -*-
import subprocess, sys

PY = sys.executable
CWD = r"d:\yuan\不锈钢网带跟单3.0"

targets = [
    "tests/unit/utils/test_excel_utils_gaps.py",
    "tests/unit/services",
]

for t in targets:
    print(f"\n{'='*60}")
    print(f"测试: {t}")
    print(f"{'='*60}")
    r = subprocess.run(
        [PY, "-m", "pytest", t, "--tb=line", "-x", "--no-cov", "-q"],
        capture_output=True, text=True, cwd=CWD, timeout=120
    )
    out = r.stdout + r.stderr
    print(out[-3000:] if len(out) > 3000 else out)
