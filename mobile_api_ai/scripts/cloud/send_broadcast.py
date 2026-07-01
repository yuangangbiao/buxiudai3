# -*- coding: utf-8 -*-
"""
发送全员通知脚本

使用方法:
    python send_broadcast.py
"""

import os
import sys
import requests
import json

def load_env():
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_file):
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())

    dat_env = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'DAT', '.env')
    if os.path.exists(dat_env):
        with open(dat_env, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())

load_env()

_mobile_url = os.environ.get('MOBILE_SERVER_URL', 'http://127.0.0.1:5003')
_content_task_link = f'👉 **<a href="{_mobile_url}/task/A1B2C3D4">点击手机端快速处理任务</a>**'
content = f"""**<big>[新任务] 张三 请查收！</big>**

---

**📋 订单：**`ORD2026050801`
**🏭 客户：**上海机械厂
**📦 产品：**100米 乙字形网带
**🔧 工序：**编织
**🎯 数量：**100
**⏰ 时间：**2026-05-10 10:30

---
{_content_task_link}

---
💡 回复 **"确认A1B2C3"** 来接收任务"""

base_url = os.getenv('DISPATCH_CENTER_URL', 'http://localhost:5003')
url = f"{base_url}/api/dispatch-center/messages/send"
payload = {"content": content, "channels": ["wechat_group"]}

print("正在发送通知...")
print(f"URL: {url}")
print(f"Content: {content[:50]}...")

try:
    resp = requests.post(url, json=payload, timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10')))
    result = resp.json()
    print("\n结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result.get('code') == 0:
        print("\n✅ 通知发送成功！")
    else:
        print(f"\n❌ 发送失败: {result.get('message', '未知错误')}")
except Exception as e:
    print(f"\n❌ 连接失败: {e}")
    print("请确认调度中心服务是否已启动 (python start_all.py 或 python wechat_server.py)")