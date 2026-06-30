import sys, os
print(f'script dir: {os.path.dirname(os.path.abspath(__file__))}')
for i, p in enumerate(sys.path):
    print(f'  [{i}] {p}')

# test import
import utils
print(f'utils.__file__ = {utils.__file__}')
print(f'utils.__path__ = {utils.__path__}')
from utils.process_monitor import start_monitor_thread
print('import utils.process_monitor OK')
