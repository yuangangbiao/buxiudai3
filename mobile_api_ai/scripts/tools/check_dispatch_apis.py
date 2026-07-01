import requests
import json

endpoints = [
    ('GET', 'http://localhost:5000/api/dispatch-center/status'),
    ('GET', 'http://localhost:5000/api/dispatch-center/tasks'),
    ('GET', 'http://localhost:5000/api/dispatch-center/operators'),
    ('GET', 'http://localhost:5000/api/dispatch-center/messages/templates'),
    ('GET', 'http://localhost:5000/api/dispatch-center/processes'),
    ('GET', 'http://localhost:5000/api/dispatch-center/rules'),
    ('GET', 'http://localhost:5000/api/dispatch-center/alerts'),
    ('GET', 'http://localhost:5000/api/dispatch-center/dispatch-log'),
    ('GET', 'http://localhost:5000/api/dispatch-center/repair-categories'),
    ('GET', 'http://localhost:5000/api/dispatch-center/repair-records'),
    ('GET', 'http://localhost:5000/api/dispatch-center/outsource-records'),
    ('GET', 'http://localhost:5000/api/dispatch-center/outsource-config'),
    ('GET', 'http://localhost:5002/container/api/stats'),
    ('GET', 'http://localhost:5002/api/operators'),
    ('GET', 'http://localhost:5002/api/v4/documents/work_order'),
]

for method, url in endpoints:
    try:
        r = requests.request(method, url, timeout=15)
        code = r.status_code
        short = url.split('/api/')[1] if '/api/' in url else url
        if code != 200:
            print(f"[{code}] FAIL  {short}")
            continue
        try:
            data = r.json()
            extra = ""
            d = data.get('data')
            if isinstance(d, list):
                extra = f" items={len(d)}"
            elif isinstance(d, dict):
                if 'tasks' in d:
                    extra = f" tasks={len(d['tasks'])}"
                elif 'total' in d:
                    extra = f" total={d['total']}"
                elif 'operators' in d:
                    extra = f" operators={len(d['operators'])}"
                elif 'summary' in d:
                    s = d['summary']
                    extra = f" total={s.get('total',0)} pending={s.get('pending',0)}"
            print(f"[{code}] OK    {short}{extra}")
        except Exception:
            print(f"[{code}] PARSE_ERR  {short}")
    except Exception as e:
        short = url.split('/api/')[1] if '/api/' in url else url
        print(f"[ERR] FAIL  {short} -> {type(e).__name__}")
