"""等 8008 catchup_alive=true"""
import time, requests
for i in range(10):
    time.sleep(5)
    try:
        r = requests.get('http://127.0.0.1:8008/health', timeout=5)
        d = r.json()
        ca = d.get('catchup_alive')
        hb = d.get('catchup_heartbeat', 0)
        print(f'  {i*5+5:3d}s catchup_alive={ca} heartbeat={hb}')
        if ca: break
    except Exception as e:
        print(f'  {i*5+5:3d}s ERR: {e}')
