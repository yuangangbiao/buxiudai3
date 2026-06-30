import ast, os, glob
from collections import defaultdict

# Scan all test files
files_imports = {}

for f in sorted(glob.glob('tests/unit/**/*.py', recursive=True)):
    if '__pycache__' in f or f.endswith('_run_native_coverage.py') or f.endswith('_run_operator_full_cov.py'):
        continue
    try:
        with open(f, 'r', encoding='utf-8') as fh:
            source = fh.read()
        tree = ast.parse(source)
        from_imports = set()
        module_imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    from_imports.add(f'{module}:{alias.name}')
        relpath = os.path.relpath(f, 'tests/unit').replace(os.sep, '/')
        files_imports[relpath] = {
            'module_imports': sorted(module_imports),
            'from_imports': sorted(from_imports)
        }
    except Exception as e:
        pass

# Source module coverage
src_modules = defaultdict(list)
for fname, data in files_imports.items():
    seen = set()
    for imp in data['from_imports']:
        mod = imp.split(':')[0]
        if mod.startswith(('models.', 'services.', 'core.', 'utils.', 'config', 'constants')):
            if mod not in seen:
                src_modules[mod].append(fname)
                seen.add(mod)
    for imp in data['module_imports']:
        if imp.startswith(('models.', 'services.', 'core.', 'utils.', 'config', 'constants')):
            if imp not in seen:
                src_modules[imp].append(fname)
                seen.add(imp)

print('=' * 80)
print('TEST FILE IMPORT ANALYSIS REPORT')
print('=' * 80)
print(f'\nTotal test files scanned: {len(files_imports)}')

dirs = defaultdict(list)
for fname in files_imports:
    d = os.path.dirname(fname) or '(root)'
    dirs[d].append(fname)

print('\n--- Files by directory ---')
for d in sorted(dirs):
    print(f'  {d}: {len(dirs[d])} files')

print('\n--- Source modules tested (by import in test files) ---')
for mod in sorted(src_modules, key=lambda m: len(src_modules[m]), reverse=True):
    files = src_modules[mod]
    print(f'  {mod}: {len(files)} test files')

# Source modules NOT imported at all
all_src = set()
for root in ['models', 'services', 'core', 'utils']:
    for f in glob.glob(f'{root}/**/*.py', recursive=True):
        if '__pycache__' in f:
            continue
        mod = f.replace(os.sep, '.').replace('.py', '')
        all_src.add(mod)

tested = set(src_modules.keys())
not_tested = sorted(all_src - tested)
print(f'\n--- Source modules NOT imported ({len(not_tested)}): ---')
for m in not_tested:
    print(f'  {m}')

print('\n--- Top 20 most tested source modules ---')
for mod, files in sorted(src_modules.items(), key=lambda x: -len(x[1]))[:20]:
    print(f'  {mod}: {len(files)} files')

# Detailed: which test files import models.order
print('\n\n--- DETAILED: test files importing models.order ---')
for fname, data in sorted(files_imports.items()):
    is_order = False
    for imp in data['from_imports']:
        if imp.startswith('models.order:'):
            is_order = True
            break
    if not is_order:
        for imp in data['module_imports']:
            if imp == 'models.order':
                is_order = True
                break
    if is_order:
        items = []
        for imp in data['from_imports']:
            if imp.startswith('models.order:'):
                items.append(imp)
        for imp in data['module_imports']:
            if imp == 'models.order':
                items.append(f'import {imp}')
        print(f'  {fname}')
        for item in sorted(items):
            print(f'    {item}')

# Detailed: which test files import models.order OrderDAO vs other symbols
print('\n\n--- DETAILED: OrderDAO importers ---')
for fname, data in sorted(files_imports.items()):
    for imp in data['from_imports']:
        if imp == 'models.order:OrderDAO':
            print(f'  {fname}')
            break
