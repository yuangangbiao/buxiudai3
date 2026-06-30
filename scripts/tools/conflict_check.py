# -*- coding: utf-8 -*-
"""冲突检查：扫描 5003 端口是否已存在 16 个待新增端点"""
import requests

BASE = "http://127.0.0.1:5003"
TIMEOUT = 3

# 16 个待新增端点（带 method）
candidates = [
    ("POST", "/api/sync/report", {}),
    ("POST", "/api/sync/report/actual", {}),
    ("POST", "/api/sync/validate/input", {}),
    ("POST", "/api/sync/outsource/publish", {}),
    ("POST", "/api/sync/delivery-date-change", {}),
    ("POST", "/api/sync/drift/check", {}),
    ("POST", "/api/sync/data/fingerprint", {}),
    ("GET", "/api/sync/circuit/status", None),
    ("POST", "/api/sync/circuit/reset", {}),
    ("GET", "/api/sync/queue/status", None),
    ("GET", "/api/sync/queue/stats", None),
    ("GET", "/api/sync/tasks/TEST001", None),
    ("POST", "/api/sync/report/confirm", {}),
    ("GET", "/api/sync/reports", None),
    ("GET", "/api/sync/logs", None),
    ("GET", "/api/sync/report/requests", None),
]

print(f"{'状态':6s} {'方法':6s} {'端点':50s} 冲突?")
print('=' * 100)
n_404 = 0
n_4xx = 0
n_5xx = 0
n_2xx = 0
for method, path, body in candidates:
    try:
        r = requests.request(method, BASE + path, json=body, timeout=TIMEOUT)
        status = r.status_code
        if status == 404:
            n_404 += 1
            conflict = "✅ 不冲突 (404)"
        elif 400 <= status < 500:
            n_4xx += 1
            conflict = f"⚠️ 已存在但参数错 ({status})"
        elif 500 <= status < 600:
            n_5xx += 1
            conflict = f"⚠️ 已存在但服务端错 ({status})"
        else:
            n_2xx += 1
            conflict = f"❌ 真冲突 (200)"
        print(f"{status:6d} {method:6s} {path:50s} {conflict}")
    except Exception as e:
        print(f"{'EXC':6s} {method:6s} {path:50s} 异常 {type(e).__name__}")

print('=' * 100)
print(f"汇总: 404={n_404} (不冲突) | 4xx={n_4xx} (已存在参数错) | 5xx={n_5xx} (已存在服务错) | 2xx={n_2xx} (真冲突)")
