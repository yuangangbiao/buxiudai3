# -*- coding: utf-8 -*-
import logging

logger = logging.getLogger(__name__)

DISPATCH_STATUS_TO_CS = {
    'created': '待排产',
    'scheduled': '已排产',
    'confirmed': '已排产',
    'in_production': '生产中',
    'reported': '质检中',
    'rejected': '已退回',
    'qc_passed': '质检通过',
    'completed': '已完成',
}

CS_ORDER_STATUS_TO_DISPATCH = {
    '待排产': 'created',
    '已排产': 'scheduled',
    '生产中': 'in_production',
    '质检中': 'reported',
    '已退回': 'rejected',
    '质检通过': 'qc_passed',
    '已完成': 'completed',
}


def map_process_to_order(process_data: dict) -> dict:
    process_id = process_data.get('id', '')
    order_no = process_data.get('order_no', '')
    dc_status = process_data.get('status', 'created')
    cs_status = DISPATCH_STATUS_TO_CS.get(dc_status, '待排产')
    return {
        'order_no': order_no,
        'dc_process_id': process_id,
        'status': cs_status,
        'dc_status': dc_status,
        'product_name': process_data.get('product_name', ''),
        'quantity': process_data.get('quantity', 0),
        'current_step': process_data.get('current_step', 0),
        'flow_type': process_data.get('flow_type', 'production'),
        'remark': process_data.get('remark', ''),
        'updated_at': process_data.get('updated_at', ''),
    }


def map_operator_to_worker(operator_data: dict) -> dict:
    operator_id = operator_data.get('id', '')
    name = operator_data.get('name', '')
    return {
        'worker_id': operator_id,
        'name': name,
        'role': operator_data.get('role', '操作员'),
        'department': operator_data.get('department', ''),
        'enabled': operator_data.get('enabled', True),
        'dc_operator_id': operator_id,
    }
