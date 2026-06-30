import subprocess
PYTHON = r'C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\python.exe'
WORK_DIR = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai'

proc = subprocess.Popen(
    [PYTHON, '-B', 'app.py'],
    cwd=WORK_DIR,
    creationflags=subprocess.CREATE_NEW_CONSOLE
)
print(f'Started 5008 PID={proc.pid}')
