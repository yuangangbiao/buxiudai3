#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试服务是否正常运行
"""
import requests
import time

services = [
    (5000, '移动报工API'),
    (5003, '企业微信机器人'),
    (5005, '大屏服务器')
]

print("="*60)
print("服务状态测试")
print("="*60)

results = []

for port, name in services:
    try:
        print(f"\n测试 {name} ({port})...")
        r = requests.get(f'http://localhost:{port}', timeout=5)
        results.append((name, port, r.status_code))
        print(f"✅ {name} OK: {r.status_code}")
    except Exception as e:
        print(f"❌ {name} 失败: {e}")
        results.append((name, port, 'ERROR'))
    time.sleep(1)

print("\n" + "="*60)
print("结果汇总:")
print("="*60)
for name, port, status in results:
    status_str = f"OK ({status})" if isinstance(status, int) else status
    print(f"{name:15s} (端口 {port}): {status_str}")
