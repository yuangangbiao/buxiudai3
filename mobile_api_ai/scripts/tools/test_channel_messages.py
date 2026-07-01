import requests, json
from datetime import datetime

BASE = 'http://127.0.0.1:5002/api/v4/messages'
now = datetime.now().strftime('%H:%M:%S')

tests = [
    {
        'label': 'AppBot - 应用机器人单独发送',
        'body': {
            'content': f'[AppBot测试 {now}] 这是应用机器人通道，发给指定用户',
            'to': '@all',
            'msg_type': 'text',
            'channel': 'app',
        },
    },
    {
        'label': 'Webhook - 群机器人单独发送',
        'body': {
            'content': f'[Webhook测试 {now}] 这是群机器人通道，发到企业微信群',
            'msg_type': 'text',
            'channel': 'webhook',
        },
    },
    {
        'label': 'AppBot - Markdown格式',
        'body': {
            'content': f'## 调度中心通知\n> 测试时间: {now}\n> 通道: <font color="info">应用机器人</font>\n> 状态: <font color="warning">测试中</font>',
            'to': '@all',
            'msg_type': 'markdown',
            'channel': 'app',
        },
    },
    {
        'label': 'Webhook - Markdown格式',
        'body': {
            'content': f'## 调度中心通知\n> 测试时间: {now}\n> 通道: <font color="comment">群机器人</font>\n> 状态: <font color="info">正常</font>',
            'msg_type': 'markdown',
            'channel': 'webhook',
        },
    },
]

for t in tests:
    print(f'--- {t["label"]} ---')
    r = requests.post(BASE, json=t['body'], timeout=15)
    result = r.json()
    status = 'OK' if result.get('code') == 0 else 'FAIL'
    channels = []
    for res in result.get('data', {}).get('results', []):
        if res.get('success'):
            channels.append(res.get('channel', '?'))
    print(f'  Status: {status} | Channels: {", ".join(channels) or "none"}')
    print(f'  Message: {result.get("message")}')
    print()

print('Done.')