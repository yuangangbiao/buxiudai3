#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试大屏页面
"""
import requests
import time

time.sleep(2)

print("=== 测试大屏页面 ===")
try:
    r = requests.get('http://localhost:5005', timeout=10)
    print(f"状态码: {r.status_code}")
    print(f"内容长度: {len(r.content)} 字节")
    print(f"内容类型: {r.headers.get('content-type')}")
    print("\n=== 页面标题 ===")
    import re
    match = re.search(r'<title>(.+?)</title>', r.text)
    if match:
        print(match.group(1))
    print("\n=== 页面预览 ===")
    print(r.text[:500])
    print("\n✅ 页面访问成功！")
except Exception as e:
    print(f"❌ 页面访问失败: {e}")
