import os, py_compile, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
files = [
    os.path.join(BASE, 'dispatch_center.py'),
    os.path.join(BASE, 'container_center', '__init__.py'),
    os.path.join(BASE, 'container_center', 'services', '__init__.py'),
    os.path.join(BASE, 'container_center', 'services', 'alert_engine.py'),
    os.path.join(BASE, 'container_center', 'api', 'configs.py'),
    os.path.join(BASE, 'container_center', 'api', 'documents.py'),
    os.path.join(BASE, 'container_center', 'api', '__init__.py'),
    os.path.join(BASE, 'container_center', 'client', 'container_client.py'),
]

errors = []
for f in files:
    try:
        py_compile.compile(f, doraise=True)
        print(f'[OK] {f.split("/")[-1]}')
    except py_compile.PyCompileError as e:
        errors.append(str(e))
        print(f'[FAIL] {f.split("/")[-1]}: {e}')

if errors:
    print(f'\n{len(errors)} file(s) failed compilation')
    sys.exit(1)
else:
    print('\nAll files compile OK')
