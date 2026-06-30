import subprocess, sys, re
result = subprocess.run(
    [sys.executable, '-m', 'pytest', 'mobile_api_ai/tests/unit/', 'mobile_api_ai/tests/integration/',
     '-v', '--tb=no', '--collect-only', '-q'],
    capture_output=True, text=True, timeout=60
)
errors = {}
for line in result.stdout.splitlines() + result.stderr.splitlines():
    if 'ModuleNotFoundError' in line or 'ImportError' in line:
        m = re.search(r"No module named '([^']+)'", line)
        if m:
            mod = m.group(1)
            errors[mod] = errors.get(mod, 0) + 1
        else:
            errors['other_import'] = errors.get('other_import', 0) + 1

total = sum(errors.values())
print(f'Total import errors: {total}')
for mod, count in sorted(errors.items(), key=lambda x: -x[1]):
    print(f'  {mod}: {count}')
