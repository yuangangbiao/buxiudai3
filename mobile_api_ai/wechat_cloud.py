# -*- coding: utf-8 -*-
"""
云端服务 - 微信回调接收 + 消息队列 + 主动发送
混合模式云端部分

启动命令: python wechat_cloud.py
"""
import os
import sys
import logging
import json
import time
import threading
from datetime import datetime

from functools import wraps
from typing import Dict
import requests
from flask import Flask, request, jsonify
from core.config import DB_PATHS, REQUEST_TIMEOUT_FAST, REQUEST_TIMEOUT_NORMAL, REQUEST_TIMEOUT_LONG, RETRY_MIN_INTERVAL, RETRY_SCHEDULER_INTERVAL, EXPIRY_TIMEOUT, EXPIRY_BATCH_LIMIT, EXPIRY_CHECK_INTERVAL, SCHEDULER_SHUTDOWN_TIMEOUT, WECHAT_CLOUD_MAX_RETRIES
from core.json_safe import require_json_content_type
from logging_setup import setup_daily_logger, cleanup_old_logs, read_log

# Flask UTF-8 配置
import flask
import atexit


def require_api_key(f):
    """API Key验证装饰器（从环境变量 WECHAT_CLOUD_API_KEY 读取）"""
    @wraps(f)
    def decorated(*args, **kwargs):
        expected = os.environ.get('WECHAT_CLOUD_API_KEY')
        if not expected:
            return jsonify({'code': 500, 'message': 'API key not configured'}), 500
        key = request.headers.get('X-API-Key') or request.args.get('api_key')
        if key != expected:
            return jsonify({'code': 403, 'message': 'Unauthorized'}), 403
        return f(*args, **kwargs)
    return decorated


app = Flask(__name__)

# 确保JSON响应使用UTF-8编码
class UTF8JSONProvider(flask.json.provider.DefaultJSONProvider):
    ensure_ascii = False

app.json_provider_class = UTF8JSONProvider
app.json = UTF8JSONProvider(app)

setup_daily_logger('wechat_cloud')
logger = logging.getLogger(__name__)

# ============== 云端备份存储（仅归档，不参与业务） ==============
from cloud_backup import (
    init_db, save_incoming_message, save_outgoing_message,
    save_callback_log, save_queue_backup, get_backup_stats
)
_init_ok = init_db()

# ============== 消息存储（数据库ACK追踪） ==============
from wechat_message_store import WechatMessageStore
_msg_store = WechatMessageStore()

# ============== 配置 ==============
API_KEY = os.getenv('WECHAT_CLOUD_API_KEY')

# ============== 本地服务URL配置 ==============
WECHAT_LOCAL_SEND_URL = os.environ.get('WECHAT_LOCAL_SEND_URL', 'http://127.0.0.1:5003/api/wechat/send')

# ============== 后台调度器阈值配置（来自 core.config） ==============

# ============== 游标轮询配置 ==============
POLL_LIMIT = int(os.getenv('POLL_LIMIT', '5'))  # 每次轮询最大拉取条数
POLL_CURSOR_MAX = int(os.getenv('POLL_CURSOR_MAX', '99999'))  # 游标到达此值后自动归零


class _BotHolder:
    """WeChatAppBot 惰性单例持有者"""
    _instance = None

    @classmethod
    def get(cls):
        if not cls._instance:
            from wechat_app_bot import WeChatAppBot
            cls._instance = WeChatAppBot(
                os.getenv('WECHAT_CORP_ID', ''),
                os.getenv('WECHAT_AGENT_ID', ''),
                os.getenv('WECHAT_SECRET', '')
            )
        return cls._instance

# ============== IP白名单配置 ==============
_ALLOWED_IPS = set()
_allow_all = os.getenv('WECHAT_ALLOW_ALL_IPS', 'false') == 'true'
_allow_list = os.getenv('WECHAT_ALLOWED_IPS', '')
if _allow_list:
    _ALLOWED_IPS.update(ip.strip() for ip in _allow_list.split(',') if ip.strip())

def _check_ip_allowed():
    """检查IP是否允许访问"""
    if _allow_all:
        return True
    if not _ALLOWED_IPS:
        return True
    remote_ip = request.remote_addr or ''
    if remote_ip == '127.0.0.1' or remote_ip.startswith('192.168.') or remote_ip.startswith('10.'):
        return True
    return remote_ip in _ALLOWED_IPS

# ============== 工具函数 ==============
def optional_api_key(f):
    """API Key验证装饰器（可选，不传也能访问）"""
    @wraps(f)
    def decorated(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated

# ============== 微信回调验证接口 ==============
@app.route('/api/wechat/hook', methods=['GET', 'POST'])
def wechat_hook():
    if not _check_ip_allowed():
        remote_ip = request.remote_addr or 'unknown'
        logger.warning(f'[安全] IP {remote_ip} 不在白名单中')
        return jsonify({'code': 403, 'message': 'IP not allowed'}), 403

    if request.method == 'GET':
        return wechat_verify()
    else:
        return wechat_callback()

def wechat_verify():
    msg_signature = request.args.get('msg_signature', '')
    timestamp = request.args.get('timestamp', '')
    nonce = request.args.get('nonce', '')
    echostr = request.args.get('echostr', '')

    logger.info(f'[验证] 收到微信验证请求: msg_signature={msg_signature}, echostr={echostr[:20]}...')

    if not echostr:
        logger.warning('[验证] 缺少echostr参数')
        return 'error', 400

    try:
        bot = _BotHolder.get()
        decrypted = bot._decrypt_message(
            echostr,
            token=os.getenv('WECHAT_TOKEN', ''),
            aes_key=os.getenv('WECHAT_AES_KEY', ''),
            msg_signature=msg_signature,
            timestamp=timestamp,
            nonce=nonce
        )
        logger.info(f'[验证] 解密echostr成功')
        return decrypted, 200
    except Exception as e:
        logger.error(f'[验证] 处理异常: {e}')
        return 'error', 400


def _save_callback_msg_to_store(xml_data, bot, msg_signature, timestamp, nonce):
    """解密回调XML并将消息保存到_msg_store供本地轮询"""
    import re
    try:
        xml_str = xml_data.decode('utf-8') if isinstance(xml_data, bytes) else xml_data

        encrypt_match = re.search(r'<Encrypt><!\[CDATA\[(.*?)\]\]></Encrypt>', xml_str)

        if encrypt_match:
            encrypt = encrypt_match.group(1)
            token = os.getenv('WECHAT_TOKEN', '')
            aes_key = os.getenv('WECHAT_AES_KEY', '')
            if not aes_key:
                logger.warning('[回调→队列] 缺少AES密钥，无法解密')
                return
            decrypted = bot._decrypt_message(
                encrypt, token, aes_key,
                msg_signature, timestamp, nonce
            )
        else:
            decrypted = xml_str

        content_match = re.search(r'<Content><!\[CDATA\[(.*?)\]\]></Content>', decrypted)
        user_match = re.search(r'<FromUserName><!\[CDATA\[(.*?)\]\]></FromUserName>', decrypted)
        msg_type_match = re.search(r'<MsgType><!\[CDATA\[(.*?)\]\]></MsgType>', decrypted)
        msg_id_match = re.search(r'<MsgId>(\d+)</MsgId>', decrypted)

        content = content_match.group(1).strip() if content_match else ''
        user_id = user_match.group(1) if user_match else ''
        msg_type = msg_type_match.group(1) if msg_type_match else 'text'
        msg_id = msg_id_match.group(1) if msg_id_match else ''

        if content and user_id:
            data = {
                'user_id': user_id,
                'content': content,
                'msg_type': msg_type,
                'msg_signature': msg_id,
                'raw_xml': decrypted[:3000]
            }
            saved_id = _msg_store.save_message(data)
            logger.info(f'[回调→队列] 消息已入队列: user={user_id}, content={content[:60]}, id={saved_id}')
        else:
            logger.info(f'[回调→队列] 跳过非文本消息: type={msg_type}, has_content={bool(content)}')
    except Exception as e:
        logger.error(f'[回调→队列] 保存消息失败: {e}')


# ============== 微信回调接口 ==============
@app.route('/api/wechat/callback', methods=['POST'])
def wechat_callback():
    """接收微信回调"""
    if not _check_ip_allowed():
        remote_ip = request.remote_addr or 'unknown'
        logger.warning(f'[安全] IP {remote_ip} 不在白名单中')
        return jsonify({'code': 403, 'message': 'IP not allowed'}), 403

    try:
        xml_data = request.data
        msg_signature = request.args.get('msg_signature', '')
        timestamp = request.args.get('timestamp', '')
        nonce = request.args.get('nonce', '')

        logger.info(f'[回调] 收到微信回调: {xml_data[:200]}')

        bot = _BotHolder.get()
        result = bot.process_callback(
            xml_data,
            token=os.getenv('WECHAT_TOKEN', ''),
            aes_key=os.getenv('WECHAT_AES_KEY', ''),
            msg_signature=msg_signature,
            timestamp=timestamp,
            nonce=nonce
        )

        logger.info(f'[回调] 处理结果: {result}')

        # === 保存消息到数据库队列（供本地轮询）===
        _save_callback_msg_to_store(xml_data, bot, msg_signature, timestamp, nonce)

        # === 备份：回调日志和入站消息 ===
        save_callback_log(msg_signature, timestamp, nonce, str(result),
                          xml_data.decode('utf-8', errors='ignore')[:3000])
        save_incoming_message(user_id='', content='(回调已处理)',
                              xml_raw=xml_data.decode('utf-8', errors='ignore')[:3000],
                              msg_signature=msg_signature)

        return 'success', 200
    except Exception as e:
        logger.error(f'[回调] 处理异常: {e}')
        save_callback_log('', '', '', f'error:{e}', '')
        return 'error', 500

# ============== 消息转发接口 (V1.0风格) ==============
@app.route('/api/forward', methods=['POST'])
def forward_message():
    """接收wechat_server转发的消息，检测求助指令转发到dispatch_center"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 400, 'message': 'Empty data'}), 400

        command_type = data.get('command_type', '')

        if command_type == 'help_request':
            logger.info(f"[转发] 检测到求助指令，转发到调度中心")
            try:
                params = data.get('params', {})
                content = data.get('content', '')
                user_id = data.get('user_id', '')
                user_name = data.get('user_name', '')
                msg_id = data.get('msg_id', '')

                dispatch_url = os.getenv('DISPATCH_CENTER_URL', 'http://127.0.0.1:5003')
                resp = requests.post(
                    f'{dispatch_url}/api/dispatch-center/help-request',
                    json={
                        'msg_id': msg_id,
                        'user_id': user_id,
                        'user_name': user_name or '',
                        'content': content,
                        'command_type': 'help_request',
                        'params': {
                            'content': params.get('content', content),
                            'original_content': params.get('original_content', content),
                            'material_info': params.get('material_info', '')
                        }
                    },
                    timeout=REQUEST_TIMEOUT_LONG
                )
                if resp.status_code == 200:
                    result = resp.json()
                    logger.info(f"[转发] 调度中心处理成功: {result}")
                    dispatch_msg = result.get('message', '您的求助已提交，请耐心等待处理')
                    try:
                        cloud_host = os.getenv('WECHAT_CLOUD_HOST', 'http://127.0.0.1:5006')
                        requests.post(f'{cloud_host}/api/response', json={
                            'to_user': user_id,
                            'content': dispatch_msg,
                            'source': 'dispatch_center'
                        }, timeout=REQUEST_TIMEOUT_FAST)
                    except Exception as re:
                        logger.error(f"[转发] 发送回复失败: {re}")
                else:
                    logger.warning(f"[转发] 调度中心返回异常: status={resp.status_code}")
            except Exception as de:
                logger.error(f"[转发] 调度中心请求失败: {de}")

        msg_id = _msg_store.save_message(data)
        if msg_id:
            logger.info(f'[转发] 消息已存入数据库: id={msg_id}')
        save_queue_backup(data)

        return jsonify({'code': 0, 'message': 'OK'})
    except Exception as e:
        logger.error(f'[转发] 处理异常: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500

@app.route('/api/queue/forward', methods=['POST'])
def forward_message_v11():
    """接收wechat_server转发的消息（V1.1兼容）"""
    return forward_message()


def _send_wechat_response(feedback: Dict):
    """发送微信响应"""
    try:
        to_user_id = feedback.get('to_user_id', '')
        message = feedback.get('message', '')
        if not to_user_id or not message:
            return
        _send_url = os.environ.get('WECHAT_SEND_URL', 'http://127.0.0.1:5003/api/wechat/send')
        resp = requests.post(
            _send_url,
            json={'content': message, 'to_user': to_user_id, 'msg_type': 'text'},
            timeout=REQUEST_TIMEOUT_NORMAL
        )
        logger.info(f'[响应] 微信消息已发送: to={to_user_id}, status={resp.status_code}')
    except Exception as e:
        logger.error(f'[响应] 发送失败: {e}')


@app.route('/api/queue/poll', methods=['GET'])
def poll_messages():
    """游标式轮询：按 SQLite rowid 顺序拉取消息（不 claim，不更改状态）"""
    try:
        since_id = int(request.args.get('since_id', '0'))
        limit = min(int(request.args.get('limit', '5')), 5)
        result = _msg_store.poll_by_cursor(since_id, limit)
        logger.info(f'[轮询] 游标轮询 since_id={since_id}, 获取 {len(result["messages"])} 条')
        result['code'] = 0
        return jsonify(result)
    except Exception as e:
        logger.error(f'[轮询] 异常: {e}')
        return jsonify({'code': -1, 'message': str(e)}), 500

@app.route('/api/poll', methods=['GET'])
def poll_messages_v10():
    """从数据库拉取消息（V1.0风格）"""
    return poll_messages()

@app.route('/api/queue/ack', methods=['POST'])
def ack_messages():
    """游标模式下 ACK 为空实现（消息不会被重复拉取）"""
    data = request.get_json() or {}
    ids = data.get('ids', [])
    if ids:
        logger.info(f'[ACK] 游标模式已忽略ACK: {len(ids)}条')
    return jsonify({'code': 0, 'message': 'OK'})

@app.route('/api/poll/ack', methods=['POST'])
def poll_ack_v10():
    """确认消息已处理（V1.0风格）"""
    return ack_messages()

# ============== 响应发送接口（通过本地5003发送微信） ==============
@app.route('/api/response', methods=['POST'])
def receive_response():
    """接收本地调度中心的回复消息，转发到本地5003发送微信"""
    try:
        data = request.get_json() or {}
        to_user = data.get('to_user')
        content = data.get('content')
        source = data.get('source', 'unknown')

        if not to_user or not content:
            return jsonify({'code': 400, 'message': 'Missing params'}), 400

        msg_id = f"RSP-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

        saved = _msg_store.save_outgoing_message(msg_id, to_user, content)
        if not saved:
            logger.warning(f'[Response] 保存消息失败: msg_id={msg_id}')

        logger.info(f'[Response] 收到回复消息: msg_id={msg_id}, to={to_user}, source={source}')

        try:
            resp = requests.post(WECHAT_LOCAL_SEND_URL, json={
                'msg_id': msg_id,
                'to_user': to_user,
                'content': content
            }, timeout=REQUEST_TIMEOUT_NORMAL)
            if resp.status_code == 200:
                logger.info(f'[Response] 已转发到本地WeChat: msg_id={msg_id}')
                return jsonify({'code': 0, 'msg_id': msg_id, 'status': 'forwarded'})
            else:
                logger.warning(f'[Response] 转发失败: status={resp.status_code}')
                return jsonify({'code': 500, 'message': 'Forward failed'}), 500
        except requests.exceptions.ConnectionError:
            logger.error(f'[Response] 无法连接到本地WeChat服务')
            return jsonify({'code': 503, 'message': 'Local server not available'}), 503
        except Exception as e:
            logger.error(f'[Response] 转发异常: {e}')
            return jsonify({'code': 500, 'message': str(e)}), 500

    except Exception as e:
        logger.error(f'[Response] 处理异常: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500

@app.route('/api/response/callback', methods=['POST'])
def response_callback():
    """微信发送回调（来自本地5003）"""
    try:
        data = request.get_json() or {}
        msg_id = data.get('msg_id')
        success = data.get('success', False)
        error = data.get('error', '')

        if not msg_id:
            return jsonify({'code': 400, 'message': 'Missing msg_id'}), 400

        logger.info(f'[Callback] 收到回调: msg_id={msg_id}, success={success}')

        if success:
            _msg_store.mark_outgoing_sent(msg_id, success=True)
            logger.info(f'[Callback] 消息已发送成功: msg_id={msg_id}')
        else:
            _msg_store.mark_outgoing_sent(msg_id, success=False, error=error)
            info = _msg_store.get_outgoing_message(msg_id)
            if info:
                retry_count = info.get('retry_count', 0)
                logger.info(f'[Callback] 消息发送失败: msg_id={msg_id}, retry={retry_count}/3')
                if retry_count >= 3:
                    _msg_store.mark_dead_message(msg_id, f'重试{retry_count}次失败: {error}')
                    logger.warning(f'[Callback] 消息已标记为死信: msg_id={msg_id}')

        return jsonify({'code': 0, 'message': 'OK'})

    except Exception as e:
        logger.error(f'[Callback] 处理异常: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500

@app.route('/api/dead', methods=['GET'])
@require_api_key
def get_dead_messages():
    """获取死信列表（供调度中心人工处理）"""
    try:
        dead_messages = _msg_store.get_dead_messages(limit=50)
        return jsonify({
            'code': 0,
            'count': len(dead_messages),
            'messages': dead_messages
        })
    except Exception as e:
        logger.error(f'[Dead] 查询异常: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500

@app.route('/api/queue/status', methods=['GET'])
@require_api_key
def queue_status():
    """获取队列状态（从数据库）"""
    try:
        stats = _msg_store.get_message_count()
        return jsonify({
            'code': 0,
            'pending': stats.get('pending', 0),
            'polled': stats.get('polled', 0),
            'processed': stats.get('processed', 0),
            'error': stats.get('error', 0)
        })
    except Exception as e:
        logger.error(f'[状态] 异常: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/messages/outgoing', methods=['GET'])
@require_api_key
def get_outgoing_messages_list():
    """获取出站消息列表"""
    try:
        status_filter = request.args.get('status')
        limit = int(request.args.get('limit', 50))

        if status_filter:
            messages = _msg_store.get_outgoing_messages_by_status(status_filter, limit=limit)
        else:
            messages = _msg_store.get_recent_outgoing_messages(limit=limit)

        return jsonify({
            'code': 0,
            'messages': messages,
            'total': len(messages)
        })
    except Exception as e:
        logger.error(f'[出站消息] 查询异常: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/messages/<msg_id>', methods=['GET'])
@require_api_key
def get_message_by_id(msg_id):
    """获取单个消息详情"""
    try:
        message = _msg_store.get_outgoing_message(msg_id)
        if message:
            return jsonify({
                'code': 0,
                'data': message
            })
        else:
            return jsonify({'code': 404, 'message': 'Message not found'}), 404
    except Exception as e:
        logger.error(f'[消息详情] 查询异常: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/messages/retry', methods=['POST'])
@require_api_key
def retry_message_send():
    """重试发送消息"""
    try:
        data = request.get_json() or {}
        msg_id = data.get('msg_id')
        force = data.get('force', False)

        if not msg_id:
            return jsonify({'code': 400, 'message': 'Missing msg_id'}), 400

        message = _msg_store.get_outgoing_message(msg_id)
        if not message:
            return jsonify({'code': 404, 'message': 'Message not found'}), 404

        if message.get('status') == 'sent' and not force:
            return jsonify({'code': 400, 'message': 'Message already sent'}), 400

        _msg_store.reset_for_retry(msg_id)

        try:
            resp = requests.post(WECHAT_LOCAL_SEND_URL, json={
                'msg_id': msg_id,
                'to_user': message.get('user_id'),
                'content': message.get('content')
            }, timeout=REQUEST_TIMEOUT_NORMAL)
            if resp.status_code == 200:
                logger.info(f'[重试] 消息已重新提交: msg_id={msg_id}')
                return jsonify({
                    'code': 0,
                    'message': '重试已提交',
                    'data': {'msg_id': msg_id, 'status': 'retrying'}
                })
            else:
                return jsonify({'code': 500, 'message': 'Forward failed'}), 500
        except Exception as e:
            logger.error(f'[重试] 转发异常: {e}')
            return jsonify({'code': 500, 'message': str(e)}), 500

    except Exception as e:
        logger.error(f'[重试] 异常: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/messages/stats', methods=['GET'])
@require_api_key
def get_message_statistics():
    """获取消息发送统计"""
    try:
        days = int(request.args.get('days', 7))
        stats = _msg_store.get_statistics(days=days)

        return jsonify({
            'code': 0,
            'data': stats
        })
    except Exception as e:
        logger.error(f'[统计] 查询异常: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500

# ============== 主动发送接口 ==============
@app.route('/api/wechat/send', methods=['POST'])
@require_api_key
def send_wechat_message():
    """主动发送微信消息"""
    try:
        data = request.get_json()
        to_user = data.get('to_user')
        content = data.get('content')
        msg_type = data.get('msg_type', 'text')

        if not to_user or not content:
            return jsonify({'code': 400, 'message': 'Missing params'}), 400

        from wechat_app_bot import WeChatAppBot
        
        # 优先使用请求体中的凭据（支持本地传入云端凭据）
        corp_id = data.pop('_corp_id', None) or os.getenv('WECHAT_CORP_ID', '')
        agent_id = data.pop('_agent_id', None) or os.getenv('WECHAT_AGENT_ID', '')
        secret = data.pop('_secret', None) or os.getenv('WECHAT_SECRET', '')
        
        if not corp_id or not agent_id or not secret:
            logger.error('[发送] 微信凭据未配置')
            return jsonify({'code': 500, 'message': '微信凭据未配置'}), 500
            
        bot = WeChatAppBot(corp_id, agent_id, secret)
        result = bot.send_text(to_user, content)

        logger.info(f'[发送] 发送消息给 {to_user}: {content[:50]}')

        # === 备份：出站消息 ===
        save_outgoing_message(to_user, content[:500], msg_type=msg_type)

        return jsonify({'code': 0, 'result': result})
    except Exception as e:
        logger.error(f'[发送] 异常: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500

@app.route('/api/wechat/send_text', methods=['POST'])
@require_api_key
def send_text():
    """发送文本消息（兼容旧接口）"""
    return send_wechat_message()


# ============== 云端代理转发 ==============
@app.route('/api/wechat/proxy_send', methods=['POST'])
@require_api_key
def proxy_send():
    """
    云端代理转发接口

    接收本地 GroupBot 的代理请求，将消息转发到企业微信 Webhook。
    本地运行时 GroupBot 检测到 WECHAT_CLOUD_HOST 非空，将消息转发至此端点。
    云服务器运行时 WECHAT_CLOUD_HOST 为空，GroupBot 直接调用 Webhook。

    请求体:
    {
        "_webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx",
        "_api_key": "<从环境变量 WECHAT_CLOUD_API_KEY 获取>",
        "msgtype": "text",
        "text": {"content": "hello"}
    }

    Returns:
        企业微信 Webhook 的原始响应
    """
    try:
        data = request.get_json(silent=True) or {}
        webhook_url = data.pop('_webhook_url', '')
        _ = data.pop('_api_key', '')

        if not webhook_url:
            logger.warning("[Proxy] 缺少 _webhook_url")
            return jsonify({'errcode': 400, 'errmsg': '缺少 _webhook_url'}), 400

        if 'msgtype' not in data:
            logger.warning("[Proxy] 缺少 msgtype 字段")
            return jsonify({'errcode': 400, 'errmsg': '缺少 msgtype 字段'}), 400

        logger.info(f"[Proxy] 转发消息到企业微信: msgtype={data.get('msgtype')}")

        resp = requests.post(
            webhook_url,
            json=data,
            timeout=REQUEST_TIMEOUT_NORMAL,
            headers={'Content-Type': 'application/json'}
        )

        result = resp.json()
        logger.info(f"[Proxy] 企业微信响应: errcode={result.get('errcode')}")

        return jsonify(result)

    except requests.exceptions.Timeout:
        logger.error("[Proxy] 转发请求超时")
        return jsonify({'errcode': 408, 'errmsg': '请求超时'}), 408
    except requests.exceptions.RequestException as e:
        logger.error(f"[Proxy] 转发请求异常: {e}")
        return jsonify({'errcode': 502, 'errmsg': f'转发失败: {str(e)}'}), 502
    except Exception as e:
        logger.error(f"[Proxy] 未知异常: {e}")
        return jsonify({'errcode': 500, 'errmsg': str(e)}), 500


# ============== 日志查看接口 ==============
@app.route('/logs', methods=['GET'])
@require_api_key
def view_logs():
    """查看日志（日日志系统）"""
    try:
        date_str = request.args.get('date')
        level = request.args.get('level')
        tail = int(request.args.get('tail', 100))

        content = read_log('wechat_cloud', date_str=date_str, tail_lines=tail, level=level)
        lines = content.split('\n') if content else []

        return jsonify({
            'code': 0,
            'total': len(lines),
            'logs': lines[-tail:]
        })
    except Exception as e:
        logger.error(f"[Logs] 读取异常: {e}")
        return jsonify({'code': 500, 'message': str(e)}), 500

# ============== 备份存储状态 ==============
@app.route('/api/backup/status', methods=['GET'])
@require_api_key
def backup_status():
    """查看备份存储状态（仅管理查阅，不参与业务）"""
    stats = get_backup_stats()
    return jsonify({
        'code': 0,
        'backup_enabled': _init_ok,
        'stats': stats
    })

def _get_access_token_from_container_center():
    """
    从容器中心获取企业微信 access_token

    容器中心所在服务器配置了 WECHAT_CORP_ID / WECHAT_AGENT_ID / WECHAT_SECRET，
    通过此函数替代本地环境变量获取 token。

    Returns:
        str or None: access_token，失败返回 None
    """
    try:
        center_url = os.environ.get('CONTAINER_CENTER_URL', 'http://localhost:5002')
        resp = requests.get(
            f'{center_url}/api/wechat/get_access_token',
            timeout=REQUEST_TIMEOUT_NORMAL
        )
        if resp.status_code != 200:
            logger.warning(f'[容器中心] 获取token HTTP {resp.status_code}')
            return None
        result = resp.json()
        if result.get('code') == 0:
            token = result.get('data', {}).get('access_token')
            if token:
                logger.info('[容器中心] 成功获取access_token')
                return token
        logger.warning(f'[容器中心] 获取token失败: {result.get("message")}')
        return None
    except requests.exceptions.ConnectionError:
        logger.warning('[容器中心] 连接失败（容器中心未启动），回退本地bot')
        return None
    except Exception as e:
        logger.warning(f'[容器中心] 获取token异常: {e}，回退本地bot')
        return None


def _proxy_contacts_from_cloud():
    """
    通过云端服务器代理获取企业微信通讯录

    当本地调用企业微信API返回60020（IP不在白名单）时，
    转发到已配置白名单的云端服务器获取。

    Returns:
        (departments_list, users_list) 或 None
    """
    try:
        cloud_host = os.environ.get('WECHAT_CLOUD_HOST', 'http://127.0.0.1:5006')
        cloud_api_key = os.environ.get('WECHAT_CLOUD_API_KEY')
        if not cloud_api_key:
            logger.error('[通讯录代理] WECHAT_CLOUD_API_KEY 环境变量未设置')
            return None
        logger.info(f'[通讯录代理] 转发到云端代理: {cloud_host}/api/wechat/users')
        resp = requests.get(
            f'{cloud_host}/api/wechat/users',
            headers={'X-API-Key': cloud_api_key},
            timeout=REQUEST_TIMEOUT_LONG
        )
        if resp.status_code != 200:
            logger.error(f'[通讯录代理] 云端返回HTTP {resp.status_code}')
            return None
        data = resp.json()
        if data.get('code') != 0:
            logger.error(f'[通讯录代理] 云端返回错误: {data.get("message")}')
            return None
        departments = data.get('departments', [])
        users = data.get('users', [])
        logger.info(f'[通讯录代理] 云端返回 {len(users)} 名用户，{len(departments)} 个部门')
        return departments, users
    except Exception as e:
        logger.error(f'[通讯录代理] 异常: {e}')
        return None


def _save_enterprise_to_container_center(departments, users):
    """
    保存企业微信架构数据到容器中心

    Args:
        departments: 部门列表
        users: 用户列表
    """
    try:
        center_url = os.environ.get('CONTAINER_CENTER_URL', 'http://localhost:5002')
        payload = {'departments': departments, 'users': users}
        resp = requests.post(
            f'{center_url}/api/enterprise/structure',
            json=payload,
            timeout=REQUEST_TIMEOUT_NORMAL
        )
        if resp.status_code == 200:
            result = resp.json()
            if result.get('code') == 0:
                logger.info('[通讯录] 企业架构已保存到容器中心')
            else:
                logger.warning(f'[通讯录] 容器中心保存失败: {result.get("message")}')
        else:
            logger.warning(f'[通讯录] 容器中心HTTP {resp.status_code}')
    except requests.exceptions.ConnectionError:
        logger.warning('[通讯录] 容器中心不可达，跳过保存')
    except Exception as e:
        logger.warning(f'[通讯录] 保存到容器中心异常: {e}')


# ============== 企业架构代理接口（接收/转发） ==============
@app.route('/cloud/org/enterprise_structure', methods=['GET', 'POST'])
@require_api_key
@require_json_content_type
def proxy_enterprise_structure():
    """
    企业架构代理接口 — 接收/转发企业微信部门人员数据

    本地端通过此接口将企业架构数据发送到云端(5006)，
    云端转发保存到容器中心(5002)做持久化缓存，并推送调度中心(5003)

    POST: 接收企业架构数据并保存到容器中心
    GET: 从容器中心读取缓存的企业架构数据

    POST Body:
        {"departments": [...], "users": [...]}

    Returns:
        {"code": 0, "message": "...", "data": {...}}
    """
    if request.method == 'GET':
        try:
            center_url = os.environ.get('CONTAINER_CENTER_URL', 'http://localhost:5002')
            resp = requests.get(
                f'{center_url}/api/enterprise/structure',
                timeout=REQUEST_TIMEOUT_NORMAL
            )
            if resp.status_code == 200:
                return jsonify(resp.json())
            return jsonify({'code': 1, 'message': f'容器中心返回 {resp.status_code}'}), 502
        except requests.exceptions.ConnectionError:
            logger.warning('[企业架构代理] 容器中心不可达')
            return jsonify({'code': 1, 'message': '容器中心不可达'}), 502
        except Exception as e:
            logger.exception(f'[企业架构代理] GET异常: {e}')
            return jsonify({'code': 500, 'message': str(e)}), 500

    try:
        body = request.get_json(silent=True) or {}
        departments = body.get('departments', [])
        users = body.get('users', [])
        logger.info(f'[企业架构代理] 收到数据: {len(departments)}个部门, {len(users)}个用户')

        if not departments and not users:
            return jsonify({'code': 1, 'message': '数据为空'})

        _save_enterprise_to_container_center(departments, users)

        return jsonify({
            'code': 0,
            'message': f'已保存 {len(departments)} 个部门, {len(users)} 个用户',
            'data': {'departments_count': len(departments), 'users_count': len(users)}
        })
    except Exception as e:
        logger.exception(f'[企业架构代理] POST异常: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


# ============== 企业微信通讯录代理接口 ==============
@app.route('/api/wechat/users', methods=['GET'])
@app.route('/api/wechat/contacts', methods=['GET'])
@require_api_key
def get_wechat_contacts():
    """
    获取企业微信通讯录（云端代理 + 容器中心缓存）

    1. 优先本地获取access_token调用企业微信API
    2. 如果本地IP不在白名单(errcode=60020)，自动转发到云端代理
    3. 获取到的数据保存到容器中心做持久化缓存

    Returns:
        {
            "code": 0,
            "users": [...],
            "departments": [...],
            "count": 10,
            "source": "local|cloud_proxy"
        }
    """
    try:
        token = _get_access_token_from_container_center()
        if not token:
            bot = _BotHolder.get()
            token = bot.get_access_token()
        if not token:
            return jsonify({'code': 500, 'message': '获取access_token失败'}), 500

        users = []
        departments = []
        source = 'local'

        dept_resp = requests.get(f'https://qyapi.weixin.qq.com/cgi-bin/department/list?access_token={token}',
            timeout=REQUEST_TIMEOUT_NORMAL)
        dept_result = dept_resp.json()

        # 检测IP白名单错误 → 转发到云端代理
        if dept_result.get('errcode') == 60020:
            logger.warning('[通讯录] 本地IP不在企业微信白名单，转发到云端代理')
            cloud_result = _proxy_contacts_from_cloud()
            if cloud_result:
                departments, users = cloud_result
                source = 'cloud_proxy'
                # 保存到容器中心
                _save_enterprise_to_container_center(departments, users)
                logger.info(f'[通讯录] 云端代理获取: {len(users)} 名用户，{len(departments)} 个部门')
                return jsonify({
                    'code': 0,
                    'users': users,
                    'departments': departments,
                    'count': len(users),
                    'source': source
                })
            return jsonify({'code': 500, 'message': '云端代理获取通讯录失败'}), 500

        if dept_result.get('errcode') == 0:
            departments = dept_result.get('department', [])

        for dept in departments:
            dept_id = dept.get('id')
            users_resp = requests.get(
                f'https://qyapi.weixin.qq.com/cgi-bin/user/simplelist?access_token={token}&department_id={dept_id}&fetch_child=1',
                timeout=REQUEST_TIMEOUT_NORMAL
            )
            users_result = users_resp.json()
            if users_result.get('errcode') == 0:
                for user in users_result.get('userlist', []):
                    user['department_name'] = dept.get('name', '')
                    users.append(user)

        logger.info(f'[通讯录] 本地获取: {len(users)} 名用户，{len(departments)} 个部门')

        # 保存到容器中心
        _save_enterprise_to_container_center(departments, users)

        return jsonify({
            'code': 0,
            'users': users,
            'departments': departments,
            'count': len(users),
            'source': source
        })

    except Exception as e:
        logger.error(f'[通讯录] 获取异常: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500

@app.route('/api/wechat/user/<user_id>', methods=['GET'])
@require_api_key
def get_wechat_user(user_id):
    """
    获取单个微信用户信息（云端代理）

    Args:
        user_id: 企业微信UserID

    Returns:
        {
            "code": 0,
            "user": {"userid": "xxx", "name": "张三", ...}
        }
    """
    try:
        bot = _BotHolder.get()

        user_info = bot.get_user_info(user_id)
        if user_info:
            return jsonify({
                'code': 0,
                'user': user_info
            })
        else:
            return jsonify({'code': 404, 'message': f'未找到用户 {user_id}'}), 404

    except Exception as e:
        logger.error(f'[用户] 获取异常: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500

@app.route('/api/wechat/user/<user_id>/name', methods=['GET'])
@require_api_key
def get_wechat_user_name(user_id):
    """
    获取微信用户名称（云端代理，快速获取姓名）

    这是一个轻量级接口，专门用于根据user_id获取用户姓名

    Args:
        user_id: 企业微信UserID

    Returns:
        {
            "code": 0,
            "userid": "xxx",
            "name": "张三"
        }
    """
    try:
        bot = _BotHolder.get()

        user_info = bot.get_user_info(user_id)
        if user_info:
            return jsonify({
                'code': 0,
                'userid': user_id,
                'name': user_info.get('name', user_id)
            })
        else:
            return jsonify({
                'code': 0,
                'userid': user_id,
                'name': user_id
            })

    except Exception as e:
        logger.error(f'[用户名] 获取异常: {e}')
        return jsonify({'code': 0, 'userid': user_id, 'name': user_id})


# ============== 健康检查 ==============
@app.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({'status': 'ok', 'time': datetime.now().isoformat()})

# ============== 启动 ==============

_scheduler_shutdown = threading.Event()
_scheduler_threads = []

def _retry_scheduler():
    """后台线程：检查失败消息并重试，60秒间隔，超过最大重试次数标记死信"""
    logger.info('[RetryScheduler] 重试调度器启动')
    _max_retries = WECHAT_CLOUD_MAX_RETRIES
    while not _scheduler_shutdown.is_set():
        try:
            failed_messages = _msg_store.get_failed_outgoing(max_retries=_max_retries, limit=10)
            for msg in failed_messages:
                msg_id = msg.get('msg_id')
                retry_count = msg.get('retry_count', 0)
                last_retry = msg.get('last_retry_at')

                if retry_count >= _max_retries:
                    _msg_store.mark_dead_message(msg_id, '超过最大重试次数')
                    logger.warning(f'[RetryScheduler] 标记死信: msg_id={msg_id}')
                    continue

                if last_retry:
                    from datetime import timedelta
                    time_since_retry = datetime.now() - datetime.fromisoformat(last_retry)
                    if time_since_retry.total_seconds() < RETRY_MIN_INTERVAL:
                        continue

                try:
                    resp = requests.post(WECHAT_LOCAL_SEND_URL, json={
                        'msg_id': msg_id,
                        'to_user': msg.get('user_id'),
                        'content': msg.get('content')
                    }, timeout=REQUEST_TIMEOUT_NORMAL)
                    if resp.status_code == 200:
                        logger.info(f'[RetryScheduler] 重试成功: msg_id={msg_id}')
                    else:
                        logger.warning(f'[RetryScheduler] 重试失败: msg_id={msg_id}, status={resp.status_code}')
                except Exception as retry_err:
                    logger.error(f'[RetryScheduler] 重试异常: msg_id={msg_id}, error={retry_err}')

        except Exception as e:
            logger.error(f'[RetryScheduler] 调度异常: {e}')

        _scheduler_shutdown.wait(timeout=RETRY_SCHEDULER_INTERVAL)

def start_retry_scheduler():
    """启动重试调度器线程"""
    t = threading.Thread(target=_retry_scheduler, daemon=True, name='RetryScheduler')
    t.start()
    _scheduler_threads.append(t)
    logger.info('[RetryScheduler] 重试调度器线程已启动')


def _expiry_checker():
    """后台线程：检查消息超时（180秒未送达），通知用户消息无法送达"""
    logger.info('[ExpiryChecker] 超时检测调度器启动')
    while not _scheduler_shutdown.is_set():
        try:
            timeout_messages = _msg_store.get_timeout_outgoing(timeout_seconds=EXPIRY_TIMEOUT, limit=EXPIRY_BATCH_LIMIT)
            for msg in timeout_messages:
                msg_id = msg.get('msg_id')
                user_id = msg.get('user_id')
                original_content = msg.get('content', '')

                logger.warning(f'[ExpiryChecker] 消息超时: msg_id={msg_id}, user={user_id}')

                _msg_store.mark_expired_message(msg_id, f'消息发送超时({EXPIRY_TIMEOUT}秒未送达)')

                try:
                    expiry_notification = f'⚠️ 您的消息因发送超时无法送达：\n{original_content[:50]}...\n\n请稍后重试或联系管理员。'
                    resp = requests.post(WECHAT_LOCAL_SEND_URL, json={
                        'msg_id': f'EXPIRY-{msg_id}',
                        'to_user': user_id,
                        'content': expiry_notification
                    }, timeout=REQUEST_TIMEOUT_NORMAL)
                    if resp.status_code == 200:
                        logger.info(f'[ExpiryChecker] 已通知用户消息超时: msg_id={msg_id}')
                    else:
                        logger.warning(f'[ExpiryChecker] 通知失败: msg_id={msg_id}, status={resp.status_code}')
                except Exception as notify_err:
                    logger.error(f'[ExpiryChecker] 通知异常: msg_id={msg_id}, error={notify_err}')

        except Exception as e:
            logger.error(f'[ExpiryChecker] 检测异常: {e}')

        _scheduler_shutdown.wait(timeout=EXPIRY_CHECK_INTERVAL)


def start_expiry_checker():
    """启动超时检测调度器线程"""
    t = threading.Thread(target=_expiry_checker, daemon=True, name='ExpiryChecker')
    t.start()
    _scheduler_threads.append(t)
    logger.info('[ExpiryChecker] 超时检测调度器线程已启动')


def _shutdown_schedulers():
    """优雅关闭所有调度器线程"""
    logger.info('[Shutdown] 开始关闭调度器线程...')
    _scheduler_shutdown.set()
    for t in _scheduler_threads:
        t.join(timeout=SCHEDULER_SHUTDOWN_TIMEOUT)
        if t.is_alive():
            logger.warning(f'[Shutdown] 线程 {t.name} 未能在{SCHEDULER_SHUTDOWN_TIMEOUT}秒内优雅退出')
    logger.info('[Shutdown] 调度器线程已关闭')


atexit.register(_shutdown_schedulers)


if __name__ == '__main__':
    from core.config import LOG_DIR, BASE_DIR
    cleanup_old_logs()
    logger.info('=' * 50)
    logger.info('云端微信服务 - 混合模式')
    logger.info('=' * 50)
    logger.info(f'API Key 已配置: {bool(API_KEY)}')
    if not API_KEY:
        logger.warning('WECHAT_CLOUD_API_KEY 未设置，API请求将返回403，请通过环境变量配置')
    logger.info(f'日志目录: {LOG_DIR}/wechat_cloud/')
    logger.info(f'备份存储: {"已启用" if _init_ok else "未启用"}')
    logger.info('=' * 50)

    start_retry_scheduler()
    start_expiry_checker()

    ssl_context = None
    cert_file = DB_PATHS['ssl_cert']
    key_file = DB_PATHS['ssl_key']
    if os.path.exists(cert_file) and os.path.exists(key_file):
        ssl_context = (cert_file, key_file)
        logger.info('SSL: 已启用')
    else:
        logger.warning('SSL: 未配置（生产环境需要配置）')

    port = int(os.getenv('FLASK_PORT', os.getenv('PORT', 5006)))

    from werkzeug.serving import make_server
    import socket
    server = make_server('0.0.0.0', port, app, threaded=True)
    server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    logger.info(f'服务启动: 0.0.0.0:{port}')
    server.serve_forever()
