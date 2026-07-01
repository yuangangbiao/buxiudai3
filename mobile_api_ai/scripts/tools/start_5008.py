import subprocess, os, time, sys

proj = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai'
os.chdir(proj)
sys.path.insert(0, proj)

env = os.environ.copy()
env['PORT'] = '5008'

print('Starting port 5008...')
proc = subprocess.Popen(
    [sys.executable, 'start_local.py'],
    cwd=proj,
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT
)
print(f'Started PID={proc.pid}')

time.sleep(5)
if proc.poll() is None:
    print('Server is running')
else:
    output = proc.stdout.read().decode('utf-8', errors='replace')
    print(f'Server exited. Output: {output[:500]}')
