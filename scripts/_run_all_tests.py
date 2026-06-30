"""全项目回归测试运行器"""
import subprocess
import sys
import os
import datetime

PYTHON = r"C:\Users\lenovo\AppData\Local\Python\bin\python.exe"
ROOT = os.getcwd()
TS = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

def run(name, args, cwd=None):
    if cwd is None:
        cwd = ROOT
    out_file = os.path.join(ROOT, 'scripts', f'_out_{name}_{TS}.txt')
    junit_file = os.path.join(ROOT, 'scripts', f'_junit_{name}_{TS}.xml')

    cmd = [PYTHON, '-m', 'pytest'] + args + ['--tb=short', f'--junitxml={junit_file}']

    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"  cmd: {' '.join(cmd)}")
    print(f"{'='*60}")

    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )

    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}\n\nEXIT: {result.returncode}")

    lines = result.stdout.splitlines()
    summary = [l for l in lines if 'passed' in l or 'failed' in l or 'error' in l]
    if summary:
        print(f"  >> {summary[-1].strip()}")
    else:
        preview = result.stdout[:300] if result.stdout else '(empty)'
        print(f"  >> {preview}")

    if result.stderr:
        print(f"  ERR: {result.stderr[:200]}")

    print(f"  Files: out={out_file}")
    print(f"         junit={junit_file}")
    return result.returncode, out_file, junit_file


results = {}

print(f"\n{'='*60}")
print(f"  Full Project Regression Tests")
print(f"  Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"  ROOT: {ROOT}")
print(f"{'='*60}")

rc, out, junit = run('root_unit', [
    'tests/unit',
    '-v', '-p', 'no:cacheprovider',
    '--ignore=tests/unit/test_event_bus_factory.py',
])
results['root_unit'] = (rc, out, junit)

rc, out, junit = run('mobile_unit', [
    'tests/unit', '-v', '-p', 'no:cacheprovider',
], cwd=os.path.join(ROOT, 'mobile_api_ai'))
results['mobile_unit'] = (rc, out, junit)

rc, out, junit = run('integration', [
    'tests/integration', '-v', '-p', 'no:cacheprovider',
])
results['integration'] = (rc, out, junit)

rc, out, junit = run('all_no_e2e', [
    'tests/', '-v', '-p', 'no:cacheprovider',
    '--ignore=tests/e2e',
])
results['all_no_e2e'] = (rc, out, junit)

print(f"\n{'='*60}")
print(f"  Summary")
print(f"{'='*60}")
all_ok = True
for name, (rc, out, junit) in results.items():
    status = 'PASS' if rc == 0 else 'FAIL'
    icon = 'OK ' if rc == 0 else '!! '
    print(f"  [{icon}] {status}  {name}")
    if rc != 0:
        all_ok = False
print(f"{'='*60}")

if all_ok:
    print("  All tests PASSED!")
else:
    print("  Some tests FAILED.")
print()
