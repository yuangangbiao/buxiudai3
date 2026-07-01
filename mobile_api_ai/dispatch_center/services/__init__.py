# -*- coding: utf-8 -*-
"""调度中心-服务层-公共函数"""

import logging
import json
import time

logger = logging.getLogger(__name__)


def _extract_items(result):
    """统一从不同格式结果中提取 items 列表"""
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        return result.get('items', result.get('data', []))
    return []


def _is_test_order(order_no):
    """判断是否为测试订单"""
    if not order_no:
        return False
    if order_no.startswith('ATTEND_') or order_no.startswith('ORD-SCAN-'):
        return True
    return False


def _get_doc_data(item):
    """从数据包中提取文档内容"""
    if not isinstance(item, dict):
        return {}
    return item.get('doc_data', item.get('data', item.get('content', {})))


def _normalize_process_steps(steps):
    """标准化工序步骤列表"""
    if not steps or not isinstance(steps, list):
        return []
    normalized = []
    for s in steps:
        if isinstance(s, dict):
            normalized.append(s)
        elif isinstance(s, str):
            normalized.append({'name': s, 'status': 'pending'})
    return normalized
