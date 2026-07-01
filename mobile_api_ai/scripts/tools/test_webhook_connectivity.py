# -*- coding: utf-8 -*-
"""验证云端5006 /api/wechat/proxy_send 链路 + Webhook URL 有效性"""
import os
import sys
import json
import requests

# 加载 .env
from dotenv import load_dotenv
load_dotenv('d:/yuan/不锈钢网带跟单3.0/.env')

api_key = os.getenv('WECHAT_CLOUD_API_KEY')
webhook = os.getenv('WECHAT_WORK_BOT_URL')
cloud_host = os.getenv('WECHAT_CLOUD_HOST', '').rstrip('/')
if not cloud_host.startswith('http'):
    cloud_host = f'http://{cloud_host}'

print(f'[配置] cloud_host = {cloud_host}')
print(f'[配置] api_key 前4位 = {api_key[:4] if api_key else "(空)"}...')
print(f'[配置] webhook_url = {webhook[:60] if webhook else "(空)"}...')
print()

url = f'{cloud_host}/api/wechat/proxy_send'
body = {
    '_webhook_url': webhook,
    'msgtype': 'text',
    'text': {'content': '[连通测试] Webhook URL 已配置并通过云端5006验证'},
}
headers = {
    'Content-Type': 'application/json',
    'X-API-Key': api_key,
}

print(f'[请求] POST {url}')
print(f'[请求体] {json.dumps(body, ensure_ascii=False, indent=2)}')
print()

try:
    resp = requests.post(url, json=body, headers=headers, timeout=15)
    print(f'[响应] HTTP {resp.status_code}')
    print(f'[响应体] {resp.text}')
except Exception as e:
    print(f'[异常] {e}')
