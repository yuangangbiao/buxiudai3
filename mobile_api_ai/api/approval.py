# -*- coding: utf-8 -*-
"""
审批模块 - 审批流程
"""
from flask import Blueprint, request, jsonify
from .auth import success, fail

bp = Blueprint('approval', __name__, url_prefix='/api/approval')

APPROVALS = [
    {'id': 1, 'type': '生产异常', 'order_no': 'ORD202604001', 'reason': '原材料质量问题', 'requester': '张三', 'request_time': '2026-04-29 09:00:00', 'status': '待审批', 'approver': '钱经理'},
    {'id': 2, 'type': '交期变更', 'order_no': 'ORD202604002', 'reason': '客户要求提前', 'requester': '李四', 'request_time': '2026-04-29 08:00:00', 'status': '待审批', 'approver': '钱经理'},
]

@bp.route('/pending', methods=['GET'])
def pending_approvals():
    return success(data={
        'approvals': APPROVALS,
        'total': len(APPROVALS),
        'page': 1,
        'page_size': 20
    })

@bp.route('/<int:approval_id>/approve', methods=['POST'])
def approve(approval_id):
    for a in APPROVALS:
        if a['id'] == approval_id:
            a['status'] = '已通过'
            a['approve_time'] = '2026-04-29 11:00:00'
            break
    return success(message='审批已通过')

@bp.route('/<int:approval_id>/reject', methods=['POST'])
def reject(approval_id):
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        data = {}
    reason = data.get('reason', '不符合条件')

    for a in APPROVALS:
        if a['id'] == approval_id:
            a['status'] = '已拒绝'
            a['reject_reason'] = reason
            a['reject_time'] = '2026-04-29 11:00:00'
            break
    return success(message='审批已拒绝')

@bp.route('/history', methods=['GET'])
def approval_history():
    return success(data={
        'approvals': [],
        'total': 0,
        'page': 1,
        'page_size': 20
    })
