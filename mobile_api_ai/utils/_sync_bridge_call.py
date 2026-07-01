# -*- coding: utf-8 -*-
"""独立子进程：调用8008同步桥"""
import sys, json, urllib.request

if len(sys.argv) < 2:
    sys.exit(1)

try:
    payload = json.loads(sys.argv[1])
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(
        'http://127.0.0.1:8008/api/sync/sub-step-report',
        data=body,
        headers={'Content-Type': 'application/json; charset=utf-8'}
    )
    urllib.request.urlopen(req, timeout=10)
except Exception:
    pass
