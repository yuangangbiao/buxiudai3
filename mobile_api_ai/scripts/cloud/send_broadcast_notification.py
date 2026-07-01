#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
发送全员通知脚本

用法:
    python send_broadcast_notification.py "通知内容"
    python send_broadcast_notification.py

示例:
    python send_broadcast_notification.py "请各部门注意，明天上午9点有会议！"
"""

import os
import sys
import requests
import json
from datetime import datetime

def load_env_config():
    """从环境变量或配置文件加载配置"""
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_file):
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())

    env_file2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'DAT', '.env')
    if os.path.exists(env_file2):
        with open(env_file2, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())

def get_base_url():
    """获取API基础URL"""
    return os.getenv('DISPATCH_CENTER_URL', 'http://localhost:5003')

def send_broadcast_notification(content: str, base_url: str = None) -> dict:
    """
    发送全员通知

    Args:
        content: 通知内容 (Markdown格式)
        base_url: API基础URL

    Returns:
        发送结果
    """
    if base_url is None:
        base_url = get_base_url()

    url = f"{base_url}/messages/send"

    payload = {
        "content": content,
        "channels": ["wechat_group"]
    }

    try:
        response = requests.post(url, json=payload, timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10')))
        result = response.json()
        return result
    except requests.exceptions.ConnectionError:
        return {'code': 500, 'message': f'无法连接到 {base_url}，请确认服务是否启动'}
    except Exception as e:
        return {'code': 500, 'message': f'发送失败: {str(e)}'}

def send_task_notification(
    order_no: str,
    customer: str,
    product: str,
    process: str,
    quantity: str,
    task_id: str = '',
    operator: str = '',
    base_url: str = None
) -> dict:
    """
    发送任务通知（按照之前展示的格式）

    Args:
        order_no: 订单号
        customer: 客户名称
        product: 产品信息
        process: 工序名称
        quantity: 数量
        task_id: 任务ID
        operator: 操作员名称
        base_url: API基础URL

    Returns:
        发送结果
    """
    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    content = f"""**<big>[新任务] {operator} 请查收！</big>**

---
**📋 订单：**`{order_no}`
**🏭 客户：**{customer}
**📦 产品：**{product}
**🔧 工序：**{process}
**🎯 数量：**{quantity}
**⏰ 时间：**{now}

---
💡 回复 **"确认{task_id[-6:] if task_id else 'XXXXXX'}"** 来接收任务"""

    return send_broadcast_notification(content, base_url)

def main():
    load_env_config()

    if len(sys.argv) > 1:
        content = sys.argv[1]
    else:
        print("=" * 60)
        print("发送全员通知")
        print("=" * 60)
        print()
        print("请输入通知内容 (Markdown格式):")
        print()
        content = input().strip()

    if not content:
        print("通知内容不能为空！")
        sys.exit(1)

    print(f"\n正在发送通知...")
    result = send_broadcast_notification(content)

    if result.get('code') == 0:
        print("✅ 通知发送成功！")
        if 'data' in result:
            print(f"   发送结果: {result['data']}")
    else:
        print(f"❌ 发送失败: {result.get('message', '未知错误')}")
        sys.exit(1)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='发送全员通知')
    parser.add_argument('--content', '-c', help='通知内容')
    parser.add_argument('--url', '-u', default='http://localhost:5003', help='API地址')
    args = parser.parse_args()

    load_env_config()

    if args.content:
        content = args.content
    else:
        print("=" * 60)
        print("发送全员通知")
        print("=" * 60)
        print()
        print("请输入通知内容 (Markdown格式):")
        print()
        content = input().strip()

    if not content:
        print("通知内容不能为空！")
        sys.exit(1)

    print(f"\n正在发送通知...")
    result = send_broadcast_notification(content, args.url)

    if result.get('code') == 0:
        print("✅ 通知发送成功！")
        if 'data' in result:
            print(f"   发送结果: {result['data']}")
    else:
        print(f"❌ 发送失败: {result.get('message', '未知错误')}")
        sys.exit(1)
