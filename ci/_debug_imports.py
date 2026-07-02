#!/usr/bin/env python3
"""Debug import chain - simulate test_v3_6_full.py behavior"""
import os
import sys
import importlib.util

os.environ['JWT_SECRET_KEY'] = 'x' * 64
PROJECT_ROOT = os.getenv('GITHUB_WORKSPACE', os.getcwd())
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'mobile_api_ai'))

print('PROJECT_ROOT:', PROJECT_ROOT)
print('sys.path[0:3]:', sys.path[0:3])
print()

def _direct_import(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod

# Simulate test script's _direct_import calls
_qv = _direct_import('utils.quantity_validator',
    os.path.join(PROJECT_ROOT, 'mobile_api_ai', 'utils', 'quantity_validator.py'))
print('After _direct_import quantity_validator:')
print('  sys.modules has utils?', 'utils' in sys.modules)
print('  sys.modules has utils.quantity_validator?', 'utils.quantity_validator' in sys.modules)
print()

_dt = _direct_import('utils.dispatch_task',
    os.path.join(PROJECT_ROOT, 'mobile_api_ai', 'utils', 'dispatch_task.py'))
print('After _direct_import dispatch_task:')
print('  sys.modules has utils?', 'utils' in sys.modules)
print('  sys.modules has utils.dispatch_task?', 'utils.dispatch_task' in sys.modules)
print()

# Now try the from import (what test functions do)
print('Trying: from utils.dispatch_task import dispatch_task')
try:
    from utils.dispatch_task import dispatch_task
    print('  OK')
except Exception as e:
    print('  FAIL -', type(e).__name__, e)

print()
print('Trying: from utils.quantity_validator import validate_quantity')
try:
    from utils.quantity_validator import validate_quantity
    print('  OK')
except Exception as e:
    print('  FAIL -', type(e).__name__, e)
