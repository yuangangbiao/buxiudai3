"""Debug utils import issue"""
import sys
print(f'sys.path[0]={sys.path[0]}')
print(f'sys.path={sys.path}')

# Find which utils will be found
import importlib.util
spec = importlib.util.find_spec('utils')
if spec:
    print(f'utils found at: {spec.origin}')
    print(f'utils submodule_search_paths: {spec.submodule_search_locations}')
else:
    print('utils NOT found')

spec2 = importlib.util.find_spec('utils.process_monitor')
if spec2:
    print(f'utils.process_monitor found at: {spec2.origin}')
else:
    print('utils.process_monitor NOT found')

# Try import
try:
    from utils.process_monitor import start_monitor_thread
    print('IMPORT OK')
except Exception as e:
    print(f'IMPORT FAILED: {e}')
