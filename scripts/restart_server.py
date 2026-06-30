import subprocess, time, urllib.request

def kill_port_5001():
    result = subprocess.run(
        ['powershell', '-Command', 'netstat -ano | Select-String ":5001 " | Select-String "LISTENING"'],
        capture_output=True, text=True, cwd=r'd:\yuan\不锈钢网带跟单3.0'
    )
    lines = result.stdout.strip().split('\n')
    pids = set()
    for line in lines:
        parts = line.strip().split()
        for p in reversed(parts):
            if p.isdigit() and int(p) > 1000:
                pids.add(int(p))
                break
    print(f'Found server PIDs on 5001: {pids}')
    for pid in pids:
        subprocess.run(['powershell', '-Command', f'Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue'])
        print(f'Killed {pid}')
    return list(pids)

def wait_server_ready(port, timeout=8):
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(f'http://localhost:{port}/', timeout=1)
            return True
        except:
            time.sleep(0.5)
    return False

port = 5001
pids = kill_port_5001()
time.sleep(2)

print('Starting server...')
subprocess.Popen(
    ['powershell', '-Command', 'Start-Process -FilePath ".\\.venv\\Scripts\\python.exe" -ArgumentList "desktop_web\\server.py" -NoNewWindow'],
    cwd=r'd:\yuan\不锈钢网带跟单3.0',
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
)
ready = wait_server_ready(port)
print(f'Server ready: {ready}')

time.sleep(1)
r = urllib.request.urlopen(f'http://localhost:{port}/shipment')
c = r.read().decode('utf-8')
checks = {
    'cFreight': 'cFreight' in c,
    'cShipQty': 'cShipQty' in c,
    'cFinishedGoods': 'cFinishedGoods' in c,
    'cOrderNo': 'cOrderNo' in c,
}
for k, v in checks.items():
    print(f'  {k}: {"✅" if v else "❌"}')
print(f'  Length: {len(c)}')
