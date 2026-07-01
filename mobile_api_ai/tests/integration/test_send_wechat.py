# -*- coding: utf-8 -*-
"""
测试脚本：通过容器中心发送5条成语接龙
"""
import requests
import json
import os
from datetime import datetime

CLOUD_HOST = os.environ.get('WECHAT_CLOUD_HOST', 'http://124.223.57.82:5006')
API_KEY = os.environ.get('WECHAT_CLOUD_API_KEY', '')
headers = {'X-API-Key': API_KEY}

def test_send_response():
    print()
    print("=" * 50)
    print("    通过容器中心发送微信消息")
    print("=" * 50)
    print()

    test_messages = [
        "一马当先",
        "先发制人",
        "人山人海",
        "海阔天空",
        "空前绝后",
    ]

    success = 0
    fail = 0

    for i, content in enumerate(test_messages, 1):
        print(f"[{i}] 发送: {content}")
        print(f"    目标: @all")
        print(f"    时间: {datetime.now().strftime('%H:%M:%S')}")

        try:
            response = requests.post(
                f'{CLOUD_HOST}/api/response',
                json={
                    'content': content,
                    'to_user': '@all',
                    'msg_type': 'text'
                },
                headers=headers,
                timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10'))
            )

            print(f"    状态: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    print(f"    [OK] 发送成功 ✅")
                    success += 1
                else:
                    print(f"    [X] 失败: {result.get('message')}")
                    fail += 1
            else:
                print(f"    [X] HTTP错误")
                fail += 1

        except Exception as e:
            print(f"    [X] 异常: {e}")
            fail += 1

        print()

    print("=" * 50)
    print(f"  完成！ 成功: {success}  失败: {fail}")
    print("=" * 50)

if __name__ == "__main__":
    test_send_response()
