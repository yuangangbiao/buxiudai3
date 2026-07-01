# -*- coding: utf-8 -*-
"""
云端群机器人转发服务 - 5004端口
负责：
1. 接收来自5006端口转发的群机器人消息
2. 发送消息到微信终端
3. 维护微信机器人连接状态

注意：此服务需要配置企业微信群机器人webhook
"""
import os
import sys
import json
import requests
from flask import Flask, request, jsonify

# 加载环境变量
try:
    from dotenv import load_dotenv
    if getattr(sys, 'frozen', False):
        env_path = os.path.join(os.path.dirname(sys.executable), '.env')
    else:
        env_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), '.env')
    load_dotenv(env_path)
except ImportError:
    pass

app = Flask(__name__)

# 群机器人配置（必须通过 .env 配置 GROUP_BOT_WEBHOOK）
GROUP_BOT_WEBHOOK = os.getenv('GROUP_BOT_WEBHOOK', '')
MAX_RETRY = 3

logger = app.logger
logger.setLevel('INFO')


def send_to_wechat_group(content, msg_type='text'):
    """发送消息到企业微信群机器人"""
    if not GROUP_BOT_WEBHOOK:
        logger.error('群机器人webhook未配置')
        return False, '群机器人webhook未配置'

    try:
        if msg_type == 'markdown':
            payload = {
                'msgtype': 'markdown',
                'markdown': {
                    'content': content
                }
            }
        else:
            payload = {
                'msgtype': 'text',
                'text': {
                    'content': content
                }
            }

        for attempt in range(MAX_RETRY):
            try:
                resp = requests.post(GROUP_BOT_WEBHOOK, json=payload, timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10')))
                result = resp.json()
                if result.get('errcode') == 0:
                    return True, '发送成功'
                else:
                    logger.warning(f'发送失败(尝试{attempt+1}): {result.get("errmsg")}')
                    if attempt < MAX_RETRY - 1:
                        import time
                        time.sleep(1)
            except requests.exceptions.RequestException as e:
                logger.warning(f'请求异常(尝试{attempt+1}): {e}')
                if attempt < MAX_RETRY - 1:
                    import time
                    time.sleep(1)

        return False, f'发送失败，已重试{MAX_RETRY}次'

    except Exception as e:
        logger.error(f'发送异常: {e}')
        return False, str(e)


@app.route('/api/send', methods=['POST'])
def handle_send():
    """处理群机器人消息发送请求"""
    try:
        payload = request.get_json()
        if not payload:
            return jsonify({'code': 400, 'message': '缺少消息内容'})

        content = payload.get('content', '')
        msg_type = payload.get('msg_type', 'text')
        to_user = payload.get('to_user', '@all')

        if not content:
            return jsonify({'code': 400, 'message': '消息内容为空'})

        logger.info(f'[群机器人] 发送消息: {content[:50]}...')

        success, message = send_to_wechat_group(content, msg_type)

        if success:
            logger.info('[群机器人] 发送成功')
            return jsonify({'code': 0, 'message': '发送成功'})
        else:
            logger.error(f'[群机器人] 发送失败: {message}')
            return jsonify({'code': -1, 'message': message})

    except Exception as e:
        logger.error(f'[群机器人] 处理异常: {e}')
        return jsonify({'code': -1, 'message': str(e)})


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'code': 0,
        'message': '群机器人转发服务运行正常',
        'port': 5004,
        'webhook_configured': bool(GROUP_BOT_WEBHOOK)
    })


# ============== [H-2/H-3 修复] 智能表格写入端点 ==============
# - 鉴权: X-API-Key 头校验
# - 幂等性: 基于 batch_id 内存去重（重启会清空；如需持久化用 Redis/SQLite）
# - 写入: 逐条调用企业微信智能表格 Webhook API
import threading

SMARTSHEET_WEBHOOK_KEY = os.getenv('WECHAT_SMARTSHEET_KEY', '')
SMARTSHEET_API_KEY = os.getenv('STATS_API_KEY', '')

# 幂等性保护：已处理 batch_id 集合
_processed_batches = set()
_batch_lock = threading.Lock()
_BATCH_MAX_SIZE = 10000  # 防止内存爆炸


def _check_already_processed(batch_id: str) -> bool:
    """线程安全地检查/记录 batch_id"""
    with _batch_lock:
        if len(_processed_batches) > _BATCH_MAX_SIZE:
            # 简单清理：清空一半（FIFO 简化）
            to_remove = list(_processed_batches)[:_BATCH_MAX_SIZE // 2]
            for bid in to_remove:
                _processed_batches.discard(bid)
        if batch_id in _processed_batches:
            return True
        _processed_batches.add(batch_id)
        return False


@app.route('/api/smartsheet/write', methods=['POST'])
def smartsheet_write():
    """
    接收 5005 转发的智能表格数据 → 调用 Webhook 写入
    Body: {
        "table_type": "production_daily_report",
        "period_key": "2026-06-04",
        "batch_id": "uuid",
        "record_hash": "sha256",
        "records": [{"f0001": "DR-...", "f0002": "2026-06-04", ...}, ...]
    }
    """
    # 鉴权
    client_key = request.headers.get('X-API-Key', '')
    if not STATS_API_KEY or client_key != STATS_API_KEY:
        logger.warning(f'[smartsheet/write] 鉴权失败: client_key={"***" if client_key else "empty"}')
        return jsonify({'code': 401, 'message': 'API Key 无效'}), 401

    # Webhook Key 校验
    if not SMARTSHEET_WEBHOOK_KEY:
        logger.error('[smartsheet/write] WECHAT_SMARTSHEET_KEY 未配置')
        return jsonify({'code': 500, 'message': 'WECHAT_SMARTSHEET_KEY 未配置'}), 500

    data = request.get_json(silent=True) or {}
    table_type = data.get('table_type', '')
    period_key = data.get('period_key', '')
    batch_id = data.get('batch_id', '')
    records = data.get('records', [])

    if not table_type:
        return jsonify({'code': 400, 'message': '缺少 table_type'}), 400
    if not isinstance(records, list):
        return jsonify({'code': 400, 'message': 'records 必须是数组'}), 400

    # 幂等性检查
    if batch_id and _check_already_processed(batch_id):
        logger.info(f'[smartsheet/write] batch_id={batch_id[:8]} 已处理，跳过')
        return jsonify({
            'code': 0,
            'message': '已处理，跳过（幂等性）',
            'batch_id': batch_id,
            'success_count': len(records),
        })

    logger.info(f'[smartsheet/write] {table_type} | period={period_key} | '
                f'batch_id={batch_id[:8] if batch_id else "none"} | records={len(records)}')

    # 逐条写入智能表格 Webhook
    webhook_url = (
        f'https://qyapi.weixin.qq.com/cgi-bin/wedoc/smartsheet/webhook'
        f'?key={SMARTSHEET_WEBHOOK_KEY}'
    )
    results = []
    success_count = 0
    fail_count = 0
    for idx, record in enumerate(records):
        try:
            payload = {
                'add_records': [{'values': record}]
            }
            resp = requests.post(webhook_url, json=payload, timeout=15)
            ret = resp.json()
            if ret.get('errcode') == 0 or ret.get('code') == 0:
                success_count += 1
                results.append({'idx': idx, 'status': 'ok', 'record_id': ret.get('record_id', '')})
            else:
                fail_count += 1
                results.append({
                    'idx': idx,
                    'status': 'failed',
                    'errcode': ret.get('errcode'),
                    'errmsg': ret.get('errmsg') or ret.get('message', '')
                })
                logger.warning(f'[smartsheet/write] 写入失败[{idx}]: {ret}')
        except Exception as e:
            fail_count += 1
            results.append({'idx': idx, 'status': 'error', 'message': str(e)})
            logger.error(f'[smartsheet/write] 写入异常[{idx}]: {e}')

    overall_code = 0 if fail_count == 0 else -1
    logger.info(f'[smartsheet/write] 完成 {table_type}: 成功 {success_count}/{len(records)}')
    return jsonify({
        'code': overall_code,
        'message': f'成功 {success_count}/{len(records)}',
        'table_type': table_type,
        'period_key': period_key,
        'batch_id': batch_id,
        'success_count': success_count,
        'fail_count': fail_count,
        'details': results[:10],  # 只返回前 10 条详情，避免响应过大
    })


if __name__ == '__main__':
    port = int(os.getenv('PORT', '5004'))
    app.run(host=os.getenv('FLASK_HOST', '0.0.0.0'), port=port, debug=False)
