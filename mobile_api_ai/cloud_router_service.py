# -*- coding: utf-8 -*-
"""
云端分类路由服务 - 5006端口
负责：
1. 接收本地发送的消息
2. 根据消息类型进行分类路由
3. 群机器人消息转发到5004端口
4. 其他消息路由到对应服务

路由规则：
- bot_type='group' → 群机器人服务 (5004端口)
- bot_type='app' → 企业微信应用服务
- 其他类型根据 route_tag 进行路由

增强特性：
- 断路器保护：转发失败自动熔断，防止雪崩
- 转发失败重试：指数退避重试，防止网络抖动丢消息
"""
import os
import sys
import json
import time
import uuid
import logging
import threading
from collections import deque
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

logger = app.logger
logger.setLevel('INFO')

# 服务配置
GROUP_BOT_HOST = os.getenv('GROUP_BOT_HOST', 'localhost')
GROUP_BOT_PORT = int(os.getenv('GROUP_BOT_PORT', '5004'))
WECHAT_APP_HOST = os.getenv('WECHAT_APP_HOST', 'localhost')
WECHAT_APP_PORT = int(os.getenv('WECHAT_APP_PORT', '5005'))

# 断路器配置
CB_FAIL_THRESHOLD = int(os.getenv('CB_FAIL_THRESHOLD', '5'))
CB_RECOVERY_TIMEOUT = int(os.getenv('CB_RECOVERY_TIMEOUT', '30'))
RETRY_MAX_TIMES = int(os.getenv('RETRY_MAX_TIMES', '5'))
RETRY_BASE_INTERVAL = int(os.getenv('RETRY_BASE_INTERVAL', '1'))


# ==================== 断路器 ====================
class SimpleCircuitBreaker:
    """简单的断路器实现
    连续失败超过阈值断开，经过恢复时间后尝试半开。
    """

    def __init__(self, name, failure_threshold=CB_FAIL_THRESHOLD, recovery_timeout=CB_RECOVERY_TIMEOUT):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = 'closed'
        self._lock = threading.Lock()

    def call(self, func, *args, **kwargs):
        with self._lock:
            if self.state == 'open':
                if time.time() - self.last_failure_time >= self.recovery_timeout:
                    logger.info(f'[断路器:{self.name}] 尝试半开状态')
                    self.state = 'half-open'
                else:
                    logger.warning(f'[断路器:{self.name}] 断路器已断开，跳过调用')
                    return {'code': -1, 'message': f'断路器已断开({self.name})'}

        try:
            result = func(*args, **kwargs)
            if result.get('code') == 0:
                with self._lock:
                    self.failure_count = 0
                    if self.state == 'half-open':
                        logger.info(f'[断路器:{self.name}] 半开调用成功，恢复关闭')
                        self.state = 'closed'
                return result
            else:
                raise Exception(result.get('message', '未知错误'))
        except Exception as e:
            with self._lock:
                self.failure_count += 1
                self.last_failure_time = time.time()
                if self.failure_count >= self.failure_threshold:
                    self.state = 'open'
                    logger.error(f'[断路器:{self.name}] 连续失败{self.failure_count}次，断路器断开')
                else:
                    logger.warning(f'[断路器:{self.name}] 调用失败({self.failure_count}/{self.failure_threshold}): {e}')
            return {'code': -1, 'message': str(e)}

    def get_status(self):
        with self._lock:
            return {
                'name': self.name,
                'state': self.state,
                'failure_count': self.failure_count,
                'failure_threshold': self.failure_threshold
            }


# 初始化断路器
cb_group = SimpleCircuitBreaker('group_bot_5004')
cb_app = SimpleCircuitBreaker('app_bot_5005')

# 重试队列
retry_queue = deque()
retry_lock = threading.Lock()
RETRY_INTERVALS = [1, 2, 4, 8, 16]


def _schedule_retry(target, payload, retry_count=0):
    """安排一次转发重试"""
    retry_item = {
        'id': str(uuid.uuid4()),
        'target': target,
        'payload': payload,
        'retry_count': retry_count,
        'max_retries': RETRY_MAX_TIMES,
        'created_at': time.time(),
        'next_retry_at': time.time() + (RETRY_INTERVALS[retry_count] if retry_count < len(RETRY_INTERVALS) else 30)
    }
    with retry_lock:
        retry_queue.append(retry_item)
    logger.info(f'[重试] 已安排重试: target={target}, 次数={retry_count}/{RETRY_MAX_TIMES}')


def _retry_worker():
    """后台重试工作线程"""
    while True:
        try:
            due_items = []
            with retry_lock:
                now = time.time()
                remaining = deque()
                for item in retry_queue:
                    if item['next_retry_at'] <= now:
                        due_items.append(item)
                    else:
                        remaining.append(item)
                retry_queue.clear()
                retry_queue.extend(remaining)

            for item in due_items:
                try:
                    result = _execute_forward(item['target'], item['payload'])
                    if result.get('code') == 0:
                        logger.info(f'[重试] 转发成功: target={item["target"]}')
                    else:
                        retry_count = item['retry_count'] + 1
                        if retry_count >= RETRY_MAX_TIMES:
                            logger.error(f'[重试] 达到最大重试次数({RETRY_MAX_TIMES})，放弃: target={item["target"]}')
                        else:
                            next_retry = time.time() + (RETRY_INTERVALS[retry_count] if retry_count < len(RETRY_INTERVALS) else 30)
                            with retry_lock:
                                item['retry_count'] = retry_count
                                item['next_retry_at'] = next_retry
                                retry_queue.append(item)
                except Exception as e:
                    logger.error(f'[重试] 执行异常: {e}')
        except Exception as e:
            logger.error(f'[重试] 工作线程异常: {e}')
        time.sleep(1)


retry_thread = threading.Thread(target=_retry_worker, daemon=True, name='retry-worker')
retry_thread.start()


# ==================== 路由函数 ====================
def forward_to_group_bot(payload):
    """转发消息到群机器人服务(5004端口)"""
    try:
        url = f'http://{GROUP_BOT_HOST}:{GROUP_BOT_PORT}/api/send'
        resp = requests.post(url, json=payload, timeout=int(os.environ.get('REQUEST_TIMEOUT_EXTRA', '30')))
        return resp.json()
    except Exception as e:
        logger.error(f'转发到群机器人失败: {e}')
        return {'code': -1, 'message': f'转发失败: {str(e)}'}


def forward_to_wechat_app(payload):
    """转发消息到企业微信应用服务"""
    try:
        url = f'http://{WECHAT_APP_HOST}:{WECHAT_APP_PORT}/api/send'
        resp = requests.post(url, json=payload, timeout=int(os.environ.get('REQUEST_TIMEOUT_EXTRA', '30')))
        return resp.json()
    except Exception as e:
        logger.error(f'转发到企业微信应用失败: {e}')
        return {'code': -1, 'message': f'转发失败: {str(e)}'}


def _execute_forward(target, payload):
    """执行一次转发（供重试队列调用）"""
    if target == 'group':
        return forward_to_group_bot(payload)
    elif target == 'app':
        return forward_to_wechat_app(payload)
    return {'code': -1, 'message': f'未知转发目标: {target}'}


def safe_forward_to_group_bot(payload):
    """断路器保护的群机器人转发"""
    return cb_group.call(forward_to_group_bot, payload)


def safe_forward_to_wechat_app(payload):
    """断路器保护的企业微信应用转发"""
    return cb_app.call(forward_to_wechat_app, payload)


# ==================== Flask 路由 ====================
@app.route('/api/wechat/send', methods=['POST'])
def handle_wechat_send():
    """处理微信消息发送（cloud_poller调用此端点，路由到5004/5005）"""
    try:
        payload = request.get_json()
        if not payload:
            return jsonify({'code': 400, 'message': '缺少消息内容'})
        bot_type = payload.get('bot_type', 'group')
        route_tag = payload.get('route_tag', '')
        logger.info(f'[路由] /api/wechat/send: bot_type={bot_type}, route_tag={route_tag}')
        if bot_type == 'group':
            result = safe_forward_to_group_bot(payload)
        elif bot_type == 'app':
            result = safe_forward_to_wechat_app(payload)
        else:
            return jsonify({'code': 400, 'message': f'未知的 bot_type: {bot_type}'})
        if result.get('code') != 0:
            _schedule_retry(bot_type, payload)
        return jsonify(result)
    except Exception as e:
        logger.error(f'[路由] /api/wechat/send 处理异常: {e}')
        return jsonify({'code': -1, 'message': str(e)})

@app.route('/api/send', methods=['POST'])
def handle_send():
    """处理消息发送请求（分类路由）"""
    try:
        payload = request.get_json()
        if not payload:
            return jsonify({'code': 400, 'message': '缺少消息内容'})

        bot_type = payload.get('bot_type', 'group')
        route_tag = payload.get('route_tag', '')

        logger.info(f'[路由] 收到消息: bot_type={bot_type}, route_tag={route_tag}')

        if bot_type == 'group':
            logger.info(f'[路由] 群机器人消息 → 转发到端口{GROUP_BOT_PORT}')
            result = safe_forward_to_group_bot(payload)
        elif bot_type == 'app':
            logger.info(f'[路由] 企业微信应用消息 → 转发到端口{WECHAT_APP_PORT}')
            result = safe_forward_to_wechat_app(payload)
        else:
            return jsonify({'code': 400, 'message': f'未知的 bot_type: {bot_type}'})

        if result.get('code') != 0:
            _schedule_retry(bot_type, payload)

        return jsonify(result)

    except Exception as e:
        logger.error(f'[路由] 处理消息异常: {e}')
        return jsonify({'code': -1, 'message': str(e)})


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'code': 0,
        'message': '分类路由服务运行正常',
        'port': 5006,
        'circuit_breakers': {
            'group_bot': cb_group.get_status(),
            'app_bot': cb_app.get_status()
        }
    })


if __name__ == '__main__':
    port = int(os.getenv('PORT', '5006'))
    app.run(host=os.getenv('FLASK_HOST', '0.0.0.0'), port=port, debug=False)
