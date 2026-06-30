# -*- coding: utf-8 -*-
"""分目录快速测试，找出失败项"""
import subprocess, sys, os

PY = sys.executable
CWD = r"d:\yuan\不锈钢网带跟单3.0"
TIMEOUT = 120

dirs = [
    ("models", "tests/unit/models"),
    ("utils", "tests/unit/utils"),
    ("core", "tests/unit/core"),
    ("services", "tests/unit/services"),
]

results = {}
for name, path in dirs:
    print(f"\n{'='*60}")
    print(f"测试: {name}")
    print(f"{'='*60}")
    try:
        r = subprocess.run(
            [PY, "-m", "pytest", path,
             "--tb=no", "--no-cov", "-q"],
            capture_output=True, text=True, cwd=CWD, timeout=TIMEOUT
        )
        out = r.stdout + r.stderr
        lines = out.strip().split("\n")
        summary = [l for l in lines if "passed" in l or "failed" in l or "error" in l or "ERROR" in l]
        results[name] = summary
        for l in summary:
            print(l)
    except subprocess.TimeoutExpired:
        print(f"⏱️  TIMEOUT (>120s)")
        results[name] = ["TIMEOUT"]
    except Exception as e:
        print(f"❌ ERROR: {e}")
        results[name] = [f"ERROR: {e}"]

print(f"\n{'='*60}")
print("总结")
print(f"{'='*60}")
for name, summary in results.items():
    print(f"{name}: {summary}")
