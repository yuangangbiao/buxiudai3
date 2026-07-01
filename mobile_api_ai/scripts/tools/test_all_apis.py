import requests
import sys

apis = [
    '/api/dispatch-center/status',
    '/api/dispatch-center/tasks',
    '/api/dispatch-center/operators',
    '/api/dispatch-center/messages/templates',
    '/api/dispatch-center/processes',
    '/api/dispatch-center/rules',
    '/api/dispatch-center/alerts',
    '/api/dispatch-center/dispatch-log',
    '/api/dispatch-center/repair-categories',
    '/api/dispatch-center/repair-records',
    '/api/dispatch-center/outsource-records',
    '/api/dispatch-center/outsource-config',
]

base = 'http://127.0.0.1:5000'
for path in apis:
    try:
        r = requests.get(base + path, timeout=15)
        code = r.status_code
        if code == 200:
            try:
                d = r.json()
                data = d.get('data', {})
                if isinstance(data, list):
                    info = f"items={len(data)}"
                elif isinstance(data, dict):
                    keys = list(data.keys())[:5]
                    info = f"keys={keys}"
                else:
                    info = str(data)[:80]
                print(f"[{code}] OK   {path}  {info}")
            except Exception:
                print(f"[{code}] OK   {path}  (non-json)")
        else:
            print(f"[{code}] FAIL {path}")
    except Exception as e:
        print(f"[ERR] FAIL {path}  {type(e).__name__}")
