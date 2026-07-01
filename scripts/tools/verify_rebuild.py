"""Verify rebuild result: compile check all modified files + run tests"""
import sys
import os
import py_compile

BASE = os.path.join(os.path.dirname(__file__), '..', '..', 'mobile_api_ai')
ROOT = os.path.join(os.path.dirname(__file__), '..', '..')

os.chdir(BASE)
print(f'[INFO] Working dir: {os.getcwd()}')
print()

def check_file(path):
    try:
        py_compile.compile(path, doraise=True)
        print(f'  [PASS] {path}')
        return True
    except py_compile.PyCompileError as e:
        print(f'  [FAIL] {path}')
        print(f'  Error: {e}')
        return False

print('[1/4] Compile check: dispatch_center.py ...')
ok = check_file('dispatch_center.py')
print()

if not ok:
    sys.exit(1)

print('[2/4] Compile check: standalone_dispatch_server.py ...')
ok = check_file('standalone_dispatch_server.py')
print()

if not ok:
    sys.exit(1)

print('[3/4] Compile check: container_center modules ...')
modules = [
    r'container_center\__init__.py',
    r'container_center\storage\__init__.py',
    r'container_center\storage\router.py',
    r'container_center\storage\document_store.py',
    r'container_center\storage\index_store.py',
    r'container_center\storage\config_store.py',
    r'container_center\storage\alert_store.py',
    r'container_center\api\__init__.py',
    r'container_center\api\app.py',
    r'container_center\client\__init__.py',
    r'container_center\client\container_client.py',
]
all_ok = True
for m in modules:
    if not check_file(m):
        all_ok = False
if all_ok:
    print('  [PASS] all container_center modules')
print()

if not all_ok:
    sys.exit(1)

print('[4/4] Run existing unit tests ...')
os.chdir(ROOT)
ret = os.system('python -m unittest discover tests -v')
print()
print('=' * 50)
if ret == 0:
    print('[PASS] All checks passed!')
else:
    print('[WARN] Some tests failed, check log above')
print('=' * 50)
