# -*- coding: utf-8 -*-
"""
企业微信消息中继服务（精简版）
云端只做消息转发，不参与业务逻辑

功能:
1. 接收企业微信回调消息
2. 暂存到 SQLite 消息队列
3. 提供 Poll/ACK 接口供本地轮询消费
4. (可选) 发送消息到企业微信

启动: python cloud_relay.py
"""
import os
import sys
import logging
import json
import re
import atexit
from datetime import datetime
import requests  # [H-3 修复] 2026-06-04: stats/push 端点需要
from flask import Flask, request, jsonify

from logging_setup import setup_daily_logger
setup_daily_logger('cloud_relay')
logger = logging.getLogger(__name__)

from wechat_message_store import WechatMessageStore
_msg_store = WechatMessageStore()

app = Flask(__name__)

# ============== 配置 ==============
API_KEY = os.getenv('WECHAT_CLOUD_API_KEY', '')


def require_api_key(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get('X-API-Key', '')
        if key != API_KEY:
            return jsonify({'code': 403, 'message': 'Forbidden'}), 403
        return f(*args, **kwargs)
    return decorated


class _BotHolder:
    _instance = None
    @classmethod
    def get(cls):
        if cls._instance is None:
            from wechat_app_bot import WeChatAppBot
            cls._instance = WeChatAppBot(
                os.getenv('WECHAT_CORP_ID', ''),
                os.getenv('WECHAT_AGENT_ID', ''),
                os.getenv('WECHAT_SECRET', '')
            )
        return cls._instance


def _decrypt_callback_xml(xml_data, msg_signature, timestamp, nonce):
    bot = _BotHolder.get()
    xml_str = xml_data.decode('utf-8') if isinstance(xml_data, bytes) else xml_data
    encrypt_match = re.search(r'<Encrypt><!\[CDATA\[(.*?)\]\]></Encrypt>', xml_str)
    if not encrypt_match:
        logger.warning('[回调] 未找到 Encrypt 字段')
        return None
    token = os.getenv('WECHAT_TOKEN', '')
    aes_key = os.getenv('WECHAT_AES_KEY', '')
    if not aes_key:
        logger.warning('[回调] 缺少 AES_KEY')
        return None
    return bot._decrypt_message(
        encrypt_match.group(1), token, aes_key,
        msg_signature, timestamp, nonce
    )


def _save_message_to_queue(decrypted_xml):
    content_match = re.search(r'<Content><!\[CDATA\[(.*?)\]\]></Content>', decrypted_xml)
    user_match = re.search(r'<FromUserName><!\[CDATA\[(.*?)\]\]></FromUserName>', decrypted_xml)
    msg_type_match = re.search(r'<MsgType><!\[CDATA\[(.*?)\]\]></MsgType>', decrypted_xml)
    msg_id_match = re.search(r'<MsgId>(\d+)</MsgId>', decrypted_xml)
    event_match = re.search(r'<Event><!\[CDATA\[(.*?)\]\]></Event>', decrypted_xml)

    content = content_match.group(1).strip() if content_match else ''
    user_id = user_match.group(1) if user_match else ''
    msg_type = msg_type_match.group(1) if msg_type_match else 'text'
    msg_id = msg_id_match.group(1) if msg_id_match else ''
    event = event_match.group(1) if event_match else ''

    if not content and not event:
        logger.info(f'[队列] 跳过非文本/非事件消息: type={msg_type}')
        return None

    data = {
        'user_id': user_id,
        'content': content or f'[event:{event}]',
        'msg_type': msg_type,
        'event': event,
        'msg_signature': msg_id,
        'raw_xml': decrypted_xml[:3000],
    }
    saved_id = _msg_store.save_message(data)
    logger.info(f'[队列] 消息已入队列: user={user_id}, type={msg_type}, id={saved_id}')
    return saved_id


# ============== 回调验证接口 ==============
@app.route('/api/wechat/hook', methods=['GET'])
def wechat_verify():
    msg_signature = request.args.get('msg_signature', '')
    timestamp = request.args.get('timestamp', '')
    nonce = request.args.get('nonce', '')
    echostr = request.args.get('echostr', '')
    if not echostr:
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
        return decrypted, 200
    except Exception as e:
        logger.error(f'[验证] 失败: {e}')
        return 'error', 400


# ============== 回调接收接口 ==============
@app.route('/api/wechat/hook', methods=['POST'])
def wechat_callback():
    try:
        xml_data = request.data
        msg_signature = request.args.get('msg_signature', '')
        timestamp = request.args.get('timestamp', '')
        nonce = request.args.get('nonce', '')

        logger.info(f'[回调] 收到消息: {xml_data[:200]}')

        decrypted = _decrypt_callback_xml(xml_data, msg_signature, timestamp, nonce)
        if decrypted:
            _save_message_to_queue(decrypted)

        return 'success', 200
    except Exception as e:
        logger.error(f'[回调] 处理异常: {e}')
        return 'error', 500


# ============== 轮询接口 ==============
@app.route('/api/queue/poll', methods=['GET'])
def poll_messages():
    try:
        limit = int(request.args.get('limit', 20))
        _msg_store.release_orphaned_polled(timeout_seconds=120)
        messages = _msg_store.claim_messages(limit)
        return jsonify({
            'code': 0,
            'messages': messages,
            'count': len(messages),
            'poll_token': messages[0].get('poll_token', '') if messages else ''
        })
    except Exception as e:
        logger.error(f'[轮询] 异常: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/queue/ack', methods=['POST'])
def ack_messages():
    try:
        data = request.get_json() or {}
        ids = data.get('ids', [])
        response_content = data.get('response_content', '')
        poll_token = data.get('poll_token', '')
        if ids:
            ok = _msg_store.mark_processed(ids, response_content, poll_token)
            if ok:
                logger.info(f'[ACK] token校验通过, 确认消息: {len(ids)}条')
            else:
                logger.warning(f'[ACK] token校验失败, 跳过确认: ids={ids}')
                return jsonify({'code': 403, 'message': 'poll_token校验失败'})
        return jsonify({'code': 0, 'message': 'OK'})
    except Exception as e:
        logger.error(f'[ACK] 异常: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/queue/status', methods=['GET'])
def queue_status():
    try:
        stats = _msg_store.get_message_count()
        return jsonify({'code': 0, 'stats': stats})
    except Exception as e:
        logger.error(f'[状态] 异常: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


# ============== 发送消息到企业微信（可选） ==============
@app.route('/api/wechat/send', methods=['POST'])
@require_api_key
def send_wechat_message():
    try:
        data = request.get_json()
        to_user = data.get('to_user')
        content = data.get('content')
        if not to_user or not content:
            return jsonify({'code': 400, 'message': '缺少 to_user 或 content'}), 400
        from wechat_app_bot import WeChatAppBot
        bot = WeChatAppBot(
            data.get('_corp_id', '') or os.getenv('WECHAT_CORP_ID', ''),
            data.get('_agent_id', '') or os.getenv('WECHAT_AGENT_ID', ''),
            data.get('_secret', '') or os.getenv('WECHAT_SECRET', '')
        )
        result = bot.send_text(to_user, content)
        logger.info(f'[发送] 消息已发送: to={to_user}')
        _msg_store.save_outgoing_message(to_user, content[:500])
        return jsonify({'code': 0, 'result': result})
    except Exception as e:
        logger.error(f'[发送] 异常: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


# ============== 统计表推送（转发到云端 5004） ==============
# [H-3 修复] 2026-06-04: 明确 API Key 鉴权机制
# - 本地 → 5005 用 WECHAT_CLOUD_API_KEY（复用现有）
# - 5005 → 云端 5004 用 STATS_API_KEY（独立）
# - 与 /api/wechat/send 鉴权机制一致
STATS_API_KEY = os.getenv('STATS_API_KEY', '')
CLOUD_5004_HOST = os.getenv('CLOUD_5004_HOST', '')
CLOUD_5004_PORT = os.getenv('CLOUD_5004_PORT', '5004')
CLOUD_5004_API_KEY = os.getenv('CLOUD_5004_API_KEY', '')


@app.route('/api/stats/push', methods=['POST'])
@require_api_key
def stats_push():
    """
    接收本地统计表数据 → 转发到云端 5004
    Body: {
        "table_type": "production_daily_report",
        "period_key": "2026-06-04",
        "batch_id": "uuid",
        "record_hash": "sha256",
        "records": [...]
    }
    """
    if not CLOUD_5004_HOST or not CLOUD_5004_API_KEY:
        logger.error('[stats/push] CLOUD_5004_HOST 或 CLOUD_5004_API_KEY 未配置')
        return jsonify({
            'code': 500,
            'message': '云端 5004 配置缺失（需在 .env 配置 CLOUD_5004_HOST 和 CLOUD_5004_API_KEY）'
        }), 500

    try:
        data = request.get_json(silent=True) or {}
        table_type = data.get('table_type', '')
        period_key = data.get('period_key', '')
        batch_id = data.get('batch_id', '')
        record_hash = data.get('record_hash', '')
        records = data.get('records', [])

        if not table_type:
            return jsonify({'code': 400, 'message': '缺少 table_type'}), 400
        if not isinstance(records, list):
            return jsonify({'code': 400, 'message': 'records 必须是数组'}), 400

        logger.info(f'[stats/push] {table_type} | period={period_key} | '
                    f'batch_id={batch_id[:8] if batch_id else "none"} | records={len(records)}')

        # 转发到云端 5004 的 /api/smartsheet/write 端点
        target_url = f'http://{CLOUD_5004_HOST}:{CLOUD_5004_PORT}/api/smartsheet/write'
        forward_payload = {
            'table_type': table_type,
            'period_key': period_key,
            'batch_id': batch_id,
            'record_hash': record_hash,
            'records': records,
        }
        forward_headers = {
            'Content-Type': 'application/json',
            'X-API-Key': CLOUD_5004_API_KEY,
        }
        forward_timeout = int(os.getenv('STATS_FORWARD_TIMEOUT', '60'))

        resp = requests.post(
            target_url,
            json=forward_payload,
            headers=forward_headers,
            timeout=forward_timeout,
        )
        result = resp.json() if resp.content else {'code': -1, 'message': 'empty response'}
        logger.info(f'[stats/push] 转发完成: {table_type} | '
                    f'云端返回 code={result.get("code")} | '
                    f'成功 {result.get("success_count", 0)}/{len(records)}')
        return jsonify(result)
    except requests.exceptions.Timeout:
        logger.error(f'[stats/push] 转发超时: {table_type}')
        return jsonify({'code': 504, 'message': '云端 5004 转发超时'}), 504
    except requests.exceptions.RequestException as e:
        logger.error(f'[stats/push] 转发网络异常: {e}')
        return jsonify({'code': 502, 'message': f'云端 5004 网络异常: {e}'}), 502
    except Exception as e:
        logger.exception(f'[stats/push] 异常: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


# ============== 健康检查 ==============
@app.route('/api/health')
def health():
    return jsonify({
        'code': 0,
        'service': 'cloud-relay',
        'time': datetime.now().isoformat(),
        'queue': _msg_store.get_message_count(),
    })


def _shutdown():
    logger.info('[Shutdown] cloud_relay 服务关闭')


atexit.register(_shutdown)

if __name__ == '__main__':
    host = os.getenv('RELAY_HOST', '0.0.0.0')
    port = int(os.getenv('RELAY_PORT', '5005'))

    logger.info('=' * 50)
    logger.info('  企业微信消息中继服务 (cloud_relay)')
    logger.info(f'  地址: http://{host}:{port}')
    logger.info('=' * 50)

    from waitress import serve
    serve(
        app,
        host=host,
        port=port,
        threads=int(os.getenv('RELAY_WORKERS', '4')),
        connection_limit=int(os.getenv('RELAY_CONN_LIMIT', '100')),
    )
