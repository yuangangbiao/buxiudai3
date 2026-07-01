import urllib.request, json, sys

BASE = 'http://localhost:5008'

tests = [
    ('GET', '/api/dashboard', None),
    ('GET', '/api/production-orders', None),
    ('GET', '/api/workers', None),
    ('GET', '/api/quality', None),
    ('GET', '/api/sub_step_records', None),
    ('GET', '/api/attendance/admin', None),
    ('GET', '/api/scan-info', 'code=test'),
]

all_ok = True
for method, path, params in tests:
    url = BASE + path
    if params:
        url += '?' + params
    try:
        r = urllib.request.urlopen(url)
        data = json.loads(r.read())
        is_list = isinstance(data, list)
        status = 'OK'
        if is_list:
            status = f'OK(array,len={len(data)})'
        elif isinstance(data, dict):
            has_code = 'code' in data
            has_data = 'data' in data
            keys = list(data.keys())[:6]
            status = f'OK(dict,keys={keys})'
        print(f'  [PASS] {method} {path} -> {status}')
    except Exception as e:
        print(f'  [FAIL] {method} {path} -> {type(e).__name__}: {str(e)[:80]}')
        all_ok = False

sys.exit(0 if all_ok else 1)
