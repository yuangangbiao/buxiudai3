# -*- coding: utf-8 -*-
"""检查 5008 中 metrics 是否多进程 / 多实例"""
import sys
import urllib.request
import json

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

BASE = 'http://127.0.0.1:5008'

# 1. 重置
req = urllib.request.Request(f'{BASE}/api/metrics/reset', method='POST',
                              headers={'Content-Type': 'application/json'})
print('reset:', urllib.request.urlopen(req, timeout=5).read().decode('utf-8')[:100])

# 2. 调一个已埋点端点 process/my-tasks (没有,所以不会涨)
req = urllib.request.Request(f'{BASE}/api/quality/types')
r1 = urllib.request.urlopen(req, timeout=5)
print('types status:', r1.status)
body = r1.read().decode('utf-8')
print('types body:', body[:80])

# 3. 调 metrics_api 的 stats 看是否有变化
req = urllib.request.Request(f'{BASE}/api/metrics/stats?minutes=5')
r2 = urllib.request.urlopen(req, timeout=5)
data = json.loads(r2.read().decode('utf-8'))
print('\nstats after 1 quality/types call:')
print(json.dumps(data, ensure_ascii=False, indent=2)[:1500])
