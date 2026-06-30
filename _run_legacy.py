import subprocess, os, sys

PY = r'C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\python.exe'
os.environ['MYSQL_PASSWORD'] = '88888888'
files = [
    'tests/e2e/test_01_auth.py',
    'tests/e2e/test_03_schedule.py',
    'tests/e2e/test_04_process.py',
    'tests/e2e/test_05_workreport.py',
    'tests/e2e/test_06_quality.py',
    'tests/e2e/test_07_inventory.py',
    'tests/e2e/test_08_shipment.py',
    'tests/e2e/test_09_dashboard.py',
    'tests/e2e/test_10_container_center.py',
    'tests/e2e/test_11_metrics.py',
]
args = [PY, '-m', 'pytest'] + files + ['-v', '--tb=short']
print('Running:', PY)
r = subprocess.run(args, creationflags=subprocess.CREATE_NO_WINDOW)
sys.exit(r.returncode)
