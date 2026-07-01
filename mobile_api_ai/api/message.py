# -*- coding: utf-8 -*-
"""
消息模块 - 消息通知
"""
from flask import Blueprint, request, jsonify
from .auth import success, fail

bp = Blueprint('message', __name__, url_prefix='/api/message')

MESSAGES = [
    {'id': 1, 'receiver_id': 'OP001', 'title': '工单完成通知', 'content': '订单ORD202604001已完成质检', 'type': '通知', 'is_read': False, 'create_time': '2026-04-29 10:00:00'},
    {'id': 2, 'receiver_id': 'OP001', 'title': '新工单分配', 'content': '您有新工单待处理', 'type': '通知', 'is_read': True, 'create_time': '2026-04-29 08:00:00'},
]

@bp.route('/list', methods=['GET'])
def message_list():
    receiver_id = request.args.get('receiver_id', 'OP001')
    messages = [m for m in MESSAGES if m['receiver_id'] == receiver_id]
    unread = len([m for m in messages if not m['is_read']])

    return success(data={
        'messages': messages,
        'total': len(messages),
        'unread_count': unread,
        'page': 1,
        'page_size': 20
    })

@bp.route('/unread-count', methods=['GET'])
def unread_count():
    receiver_id = request.args.get('receiver_id', 'OP001')
    count = len([m for m in MESSAGES if m['receiver_id'] == receiver_id and not m['is_read']])
    return success(data={'count': count})

@bp.route('/<int:msg_id>/read', methods=['POST'])
def mark_read(msg_id):
    for m in MESSAGES:
        if m['id'] == msg_id:
            m['is_read'] = True
            break
    return success(message='已标记为已读')
