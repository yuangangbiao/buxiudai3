#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
云端代理发送测试
通过云端服务器(124.223.57.82:5003)转发微信通知
解决本地公网IP不在企业微信白名单的问题 (error 60020)

云端服务器的IP已在企业微信管理后台加入IP白名单
所有微信API请求通过云服务器转发
"""
import requests
import json
import os
import sys
from datetime import datetime

CLOUD_HOST = os.environ.get('WECHAT_CLOUD_HOST', 'http://124.223.57.82:5003')
API_KEY = os.environ.get('WECHAT_CLOUD_API_KEY', '')

# ============== 从.env读取配置 ==============
ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
WECHAT_WEBHOOK_URL = os.environ.get('WECHAT_WORK_BOT_URL', '')

if os.path.exists(ENV_FILE):
    with open(ENV_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, _, val = line.partition('=')
            key = key.strip()
            val = val.strip()
            if key == 'WECHAT_WORK_BOT_URL':
                WECHAT_WEBHOOK_URL = val


def print_sep(title):
    """打印分隔线"""
    print()
    print('=' * 60)
    print(f'  {title}')
    print('=' * 60)


def cloud_api(endpoint, data=None, method='POST'):
    """
    调用云端服务器API

    Args:
        endpoint: API路径 (如 /api/wechat/send)
        data: POST数据 (dict)
        method: 请求方法

    Returns:
        dict: 响应数据, 或 None(失败)
    """
    url = CLOUD_HOST + endpoint
    headers = {
        'X-API-Key': API_KEY,
        'Content-Type': 'application/json'
    }
    try:
        if method == 'GET':
            r = requests.get(url, headers=headers, timeout=int(os.environ.get('REQUEST_TIMEOUT_LONG', '15')))
        else:
            r = requests.post(url, json=data, headers=headers, timeout=int(os.environ.get('REQUEST_TIMEOUT_LONG', '15')))
        return r.json()
    except requests.exceptions.Timeout:
        print(f'  [超时] 云端API调用超时: {endpoint}')
        return None
    except requests.exceptions.ConnectionError:
        print(f'  [连接失败] 无法连接云端服务器: {CLOUD_HOST}')
        return None
    except Exception as e:
        print(f'  [异常] {e}')
        return None


# ============================================================
#  测试步骤
# ============================================================

def test_health():
    """测试云端服务器连通性"""
    print_sep('1. 云端健康检查')
    try:
        r = requests.get(CLOUD_HOST + '/health', timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        result = r.json()
        if result.get('status') == 'ok':
            print(f'  [OK] 云端服务器连接正常')
            print(f'       时间: {result.get("time")}')
            return True
        else:
            print(f'  [异常] 响应异常: {result}')
            return False
    except Exception as e:
        print(f'  [失败] 无法连接云端服务器: {e}')
        return False


def test_send_app_message(to_user='@all', content=None):
    """
    通过云端发送企业微信应用消息

    Args:
        to_user: 用户ID, @all=全部用户
        content: 消息内容

    Returns:
        bool: 是否发送成功
    """
    print_sep(f'2. 发送应用消息 (给 {to_user})')
    if content is None:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        content = (
            '【系统通知】生产任务完成\n'
            '任务ID: TASK-DEMO-001\n'
            f'时间: {now}\n'
            '结果: 通过云端服务器转发'
        )

    result = cloud_api('/api/wechat/send', {
        'to_user': to_user,
        'content': content,
        'msg_type': 'text'
    })

    if result is None:
        return False

    code = result.get('code')
    message = result.get('message', '')
    send_result = result.get('result', False)

    if code == 0 and send_result:
        print(f'  [OK] 消息发送成功!')
        return True
    elif code == 0 and not send_result:
        print(f'  [警告] API调用成功但发送结果异常')
        print(f'  完整响应: {json.dumps(result, ensure_ascii=False)}')
        return False
    else:
        print(f'  [失败] code={code}, message={message}')
        return False


def test_proxy_webhook(webhook_url=None):
    """
    通过云端代理发送群机器人消息

    Args:
        webhook_url: 群机器人Webhook URL

    Returns:
        bool: 是否发送成功
    """
    print_sep('3. 云端代理群消息')
    webhook_url = webhook_url or WECHAT_WEBHOOK_URL

    if not webhook_url:
        print(f'  [跳过] 未配置 WECHAT_WORK_BOT_URL')
        return False

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    result = cloud_api('/api/wechat/proxy_send', {
        '_webhook_url': webhook_url,
        '_api_key': API_KEY,
        'msgtype': 'text',
        'text': {
            'content': f'【系统通知】通过云端代理\n时间: {now}\n云端服务器转发测试'
        }
    })

    if result is None:
        return False

    errcode = result.get('errcode')
    errmsg = result.get('errmsg', '')

    if errcode == 0:
        print(f'  [OK] 群消息发送成功!')
        return True
    else:
        print(f'  [失败] errcode={errcode}, errmsg={errmsg}')
        return False


def test_queue_status():
    """查看云端消息队列状态"""
    print_sep('4. 云端消息队列状态')
    result = cloud_api('/api/queue/status', method='GET')

    if result is None:
        return

    print(f'  队列大小: {result.get("queue_size", "?")}')
    print(f'  最大容量: {result.get("max_size", "?")}')


def parse_wechat_user_info():
    """
    尝试通过云端获取企业微信用户信息
    注意：/api/wechat/users 接口在 wechat_server.py (本地5003) 上
    云端 wechat_cloud.py 没有此接口
    """
    print_sep('5. 获取微信用户列表 (通过云端)')
    print(f'  [注意] 云端服务器没有 /api/wechat/users 接口')
    print(f'  如需获取用户列表，请通过以下方式:')
    print(f'  方案1: 在企业微信管理后台查看')
    print(f'  方案2: 确保云端 wechat_cloud.py 添加 /api/wechat/users 路由')
    print(f'  方案3: 直接修改云端代码调用企业微信API')
    return False


# ============================================================
#  主流程
# ============================================================

def run_all_tests():
    """运行所有测试"""
    print()
    print('★' * 30)
    print('  企业微信云端代理发送测试')
    print(f'  云端服务器: {CLOUD_HOST}')
    print(f'  测试时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('★' * 30)

    results = {}

    results['health'] = test_health()
    if not results['health']:
        print()
        print('[终止] 云端服务器不可达，无法继续测试')
        return results

    results['app_message'] = test_send_app_message('@all')
    results['webhook'] = test_proxy_webhook()
    test_queue_status()
    parse_wechat_user_info()

    # ============== 汇总 ==============
    print()
    print('=' * 60)
    print('  测试汇总')
    print('=' * 60)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    for name, ok in results.items():
        status = '[OK]' if ok else '[FAIL]'
        print(f'  {status} {name}')
    print(f'  ---')
    print(f'  通过: {passed}/{total}')

    return results


if __name__ == '__main__':
    run_all_tests()
