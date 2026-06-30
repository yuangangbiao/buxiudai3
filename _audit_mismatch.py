"""audit: test files vs production code mismatches"""
import os, re, sys

base = 'D:/yuan/不锈钢网带跟单3.0'
sys.path.insert(0, base + '/mobile_api_ai')

# ===== 1. Template count =====
from template_engine import MESSAGE_TEMPLATES_DEFAULT
actual_tmpl = len(MESSAGE_TEMPLATES_DEFAULT)
print(f'[1] 模板: 实际={actual_tmpl}')

# ===== 2. Test assertion checks =====
tmpl_test = base + '/tests/unit/test_template_engine.py'
with open(tmpl_test, encoding='utf-8') as f:
    text = f.read()
match = re.search(r'assert len\(MESSAGE_TEMPLATES_DEFAULT\) == (\d+)', text)
if match:
    expected = int(match.group(1))
    print(f'[1] 测试断言={expected} 实际={actual_tmpl}', 'OK' if expected == actual_tmpl else 'MISMATCH')

# ===== 3. Scan for dead imports in tests =====
print('\n[2] Import from dead modules:')
dead_imports = []
for root, dirs, files in os.walk(base + '/tests'):
    for f in files:
        if not f.endswith('.py') or 'test_' not in f:
            continue
        path = os.path.join(root, f)
        try:
            text = open(path, encoding='utf-8').read()
        except:
            continue
        for m in re.finditer(r'from\s+(\S+)\s+import', text):
            mod = m.group(1).strip()
            if mod.startswith('.'):
                continue
            top = mod.split('.')[0]
            if top == 'dispatch_center' and mod == 'dispatch_center':
                continue  # resolves to directory
            if top in ('unittest', 'pytest', 'json', 'os', 'sys', 're', 'datetime',
                       'mock', 'requests', 'sqlite3', 'pymysql', 'threading', 'time',
                       'collections', 'io', 'typing', 'logging', 'copy', 'math',
                       'uuid', 'hashlib', 'base64', 'random', 'shutil', 'tempfile',
                       'pathlib', 'decimal', 'itertools', 'functools', 'contextlib',
                       'flask', 'werkzeug', 'dotenv', '__future__', 'builtins',
                       'inspect', 'warnings', 'enum', 'dataclasses', 'freezegun'):
                continue
            # Check if module exists
            try:
                from importlib.util import find_spec
                spec = find_spec(top)
                if spec is None:
                    dead_imports.append(f'{os.path.basename(root)}/{f}: from {mod}')
            except:
                pass

if dead_imports:
    for d in dead_imports[:20]:
        print(f'  {d}')
    print(f'  ... {len(dead_imports)} total')
else:
    print('  0 dead imports')

# ===== 4. Check for nonexistent file references =====
print('\n[3] Invalid file paths in tests:')
bad_paths = []
for root, dirs, files in os.walk(base + '/tests'):
    for f in files:
        if not f.endswith('.py'):
            continue
        path = os.path.join(root, f)
        try:
            text = open(path, encoding='utf-8').read()
        except:
            continue
        for m in re.finditer(r'["\']([^"\']*\.(?:json|db|sqlite|yaml|yml|ini|cfg))["\']', text):
            ref = m.group(1)
            if os.path.isabs(ref):
                if not os.path.exists(ref):
                    bad_paths.append(f'{f}: {ref}')
            elif ref.startswith('.'):
                full = os.path.normpath(os.path.join(os.path.dirname(path), ref))
                if not os.path.exists(full):
                    bad_paths.append(f'{f}: {ref}')

if bad_paths:
    for b in bad_paths[:10]:
        print(f'  {b}')
else:
    print('  0 invalid paths')

# ===== 5. Quick pytest run =====
print('\n[4] Running tests...')
import subprocess
result = subprocess.run(
    [sys.executable, '-m', 'pytest', '-q', '--no-cov', '--tb=no'],
    cwd=base, capture_output=True, text=True, timeout=30
)
# Parse last lines
lines = [l for l in result.stdout.split('\n') if 'passed' in l or 'failed' in l]
print('  ' + '; '.join(lines[-3:]))

print('\nDone.')
