import urllib.request, json, sys

# Check all the APIs the frontend calls
apis = [
    '/api/dashboard',
    '/api/production-orders',
    '/api/workers',
    '/api/quality',
    '/api/sub_step_records',
    '/api/attendance/admin',
    '/api/scan-info?code=test',
]

for path in apis:
    url = f'http://localhost:5008{path}'
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = resp.read().decode('utf-8')
            status = resp.status
            print(f'{path} -> HTTP {status}, len={len(data)}')
            if len(data) < 500:
                print(f'  body: {data[:300]}')
            else:
                print(f'  body: {data[:200]}...')
    except Exception as e:
        print(f'{path} -> ERROR: {e}')
