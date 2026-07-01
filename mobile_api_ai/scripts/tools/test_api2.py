import urllib.request, json, sys

BASE = 'http://localhost:5008'
out_file = r'D:\api_test_result.txt'

tests = [
    ('GET', '/api/dashboard', ''),
    ('GET', '/api/production-orders', ''),
    ('GET', '/api/workers', ''),
    ('GET', '/api/quality', ''),
    ('GET', '/api/sub_step_records', ''),
    ('GET', '/api/attendance/admin', ''),
]

lines = []
all_ok = True
for method, path, params in tests:
    url = BASE + path
    if params:
        url += '?' + params
    try:
        r = urllib.request.urlopen(url)
        data = json.loads(r.read())
        is_list = isinstance(data, list)
        if is_list:
            lines.append(f'[PASS] {method} {path} -> array, len={len(data)}')
            if len(data) > 0:
                lines.append(f'  first item keys: {list(data[0].keys())[:10]}')
        elif isinstance(data, dict):
            keys = list(data.keys())
            lines.append(f'[PASS] {method} {path} -> dict, keys={keys[:8]}')
    except Exception as e:
        lines.append(f'[FAIL] {method} {path} -> {type(e).__name__}: {str(e)[:100]}')
        all_ok = False

with open(out_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

sys.exit(0 if all_ok else 1)
