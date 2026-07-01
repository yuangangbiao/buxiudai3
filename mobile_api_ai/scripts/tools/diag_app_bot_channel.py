# -*- coding: utf-8 -*-
"""
诊断云端 5006 /api/wechat/send 失败根因
模拟 dispatch_center 业务消息链路：
  业务接口 -> _send_wechat_message -> cloud_poller.send_message -> /api/wechat/send
"""
import os
import sys
import json
import requests
from dotenv import load_dotenv

load_dotenv('d:/yuan/不锈钢网带跟单3.0/.env')

api_key = os.getenv('WECHAT_CLOUD_API_KEY')
corp_id = os.getenv('WECHAT_CORP_ID', '')
agent_id = os.getenv('WECHAT_AGENT_ID', '')
secret = os.getenv('WECHAT_SECRET', '')
cloud_host = 'http://124.223.57.82:5006'

print('===== 诊断一：直接打 /api/wechat/send (不带 _corp_id 字段) =====')
print(f'本地 corp_id={corp_id!r} agent_id={agent_id!r} secret={"(空)" if not secret else "(已配置)"}')
print()

# 测试1: 不传 corp_id 字段（让云端 5006 读自己环境变量）
payload1 = {
    'to_user': '@all',
    'content': '[诊断测试1] 不带 corp_id，看云端 5006 是否有自身配置',
    'msg_type': 'text',
    'bot_type': 'app',
}
print(f'[请求体] {json.dumps(payload1, ensure_ascii=False)}')
try:
    resp = requests.post(
        f'{cloud_host}/api/wechat/send',
        json=payload1,
        headers={'Content-Type': 'application/json', 'X-API-Key': api_key},
        timeout=15,
    )
    print(f'[响应] HTTP {resp.status_code}')
    print(f'[响应体] {resp.text}')
except Exception as e:
    print(f'[异常] {e}')
print()

# 测试2: 传 corp_id 字段（模拟 cloud_poller 打包的本地凭据）
print('===== 诊断二：传 _corp_id/_agent_id/_secret 字段 (本地凭据) =====')
payload2 = {
    'to_user': '@all',
    'content': '[诊断测试2] 传 corp_id 字段',
    'msg_type': 'text',
    'bot_type': 'app',
    '_corp_id': corp_id,
    '_agent_id': agent_id,
    '_secret': secret,
}
print(f'[请求体] {json.dumps(payload2, ensure_ascii=False)}')
try:
    resp = requests.post(
        f'{cloud_host}/api/wechat/send',
        json=payload2,
        headers={'Content-Type': 'application/json', 'X-API-Key': api_key},
        timeout=15,
    )
    print(f'[响应] HTTP {resp.status_code}')
    print(f'[响应体] {resp.text}')
except Exception as e:
    print(f'[异常] {e}')
print()

# 测试3: 看云端 5006 是否配置了企业微信凭据 (通过 gettoken 试探)
print('===== 诊断三：直接调用企业微信 gettoken API 看云端 server 配置 =====')
print('无法直接看云端 5006 的环境变量，但可通过响应推测：')
print('  - 如果诊断一返回 "微信凭据未配置" → 云端 5006 自身无 corp_id 配置')
print('  - 如果诊断一返回 200/0 → 云端 5006 自身有 corp_id 配置，应用消息通道可用')
print('  - 如果诊断一返回 400/异常 → 云端 5006 有 corp_id 但调用企业微信 API 出错（IP白名单？secret过期？）')
