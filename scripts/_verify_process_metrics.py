import urllib.request, json, time

BASE = 'http://127.0.0.1:5008'

def call(path, method='GET', data=None):
    req = urllib.request.Request(BASE + path, method=method)
    if data is not None:
        req.add_header('Content-Type', 'application/json')
        req.data = json.dumps(data).encode()
    try:
        r = urllib.request.urlopen(req, timeout=8)
        return r.status, r.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', errors='replace')

print('=== step1 reset metrics ===')
code, body = call('/api/metrics/reset', 'POST')
print('  reset code=%s body=%s' % (code, body[:160]))

print()
print('=== step2 my-tasks normal (worker_id=test_001) ===')
code, body = call('/api/process/my-tasks?worker_id=test_001')
print('  my-tasks code=%s body=%s' % (code, body[:240]))

print()
print('=== step3 my-tasks missing param (400) ===')
code, body = call('/api/process/my-tasks')
print('  my-tasks code=%s body=%s' % (code, body[:200]))

print()
print('=== step4 my-tasks normal (worker_id=test_002) ===')
code, body = call('/api/process/my-tasks?worker_id=test_002')
print('  my-tasks code=%s body=%s' % (code, body[:200]))

print()
print('=== step5 check /api/metrics/stats ===')
time.sleep(1)
code, body = call('/api/metrics/stats?minutes=5')
print('  stats code=%s' % code)
data = json.loads(body).get('data', {})
api = data.get('api', {})
reports = data.get('reports', {})
errors = data.get('errors', {})
print('  api.total_requests      =', api.get('total_requests'))
print('  api.status_codes        =', api.get('status_codes'))
print('  api.top_endpoints       =', api.get('top_endpoints'))
print('  api.avg_duration_ms     =', api.get('avg_duration_ms'))
print('  api.error_rate          =', api.get('error_rate'))
print('  reports.total           =', reports.get('total'))
print('  reports.success         =', reports.get('success'))
print('  reports.failed          =', reports.get('failed'))
print('  errors.total            =', errors.get('total'))
print('  errors.by_type          =', errors.get('by_type'))
print()
print('=== step6 health ===')
code, body = call('/api/metrics/health')
print('  health code=%s body=%s' % (code, body[:200]))
