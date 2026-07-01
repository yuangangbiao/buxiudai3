# -*- coding: utf-8 -*-
"""
产线映射表（C-2.6 修复）
- process_records 没有 line 字段（customer_group 是客户分组，不是产线）
- 方案 A: 用工单号前缀映射
- 方案 B: 用硬编码的"产品类型 → 产线"映射
- 后续如需更精确，可新建 production_lines 表
"""
import re
from typing import Optional


# 工单号前缀 → 产线
WO_PREFIX_TO_LINE = {
    'WO-L1': '网带一线',
    'WO-L2': '网带二线',
    'WO-L3': '网带三线',
    'WO-PLT': '平板线',
    'WO-CHAIN': '链板线',
}


# 产品类型 → 产线（兜底）
PRODUCT_TYPE_TO_LINE = {
    '平板型网带': '网带一线',
    '链板型网带': '网带二线',
    '输送带': '网带三线',
}


def get_line_by_order_no(order_no: str) -> Optional[str]:
    """根据工单号前缀获取产线"""
    if not order_no:
        return None
    # 尝试前缀匹配
    for prefix, line in WO_PREFIX_TO_LINE.items():
        if order_no.startswith(prefix):
            return line
    # 尝试解析工单号中包含的产线代号
    match = re.search(r'L(\d+)', order_no)
    if match:
        return f'网带{match.group(1)}线'
    return None


def get_line_by_product(product_name: str) -> Optional[str]:
    """根据产品名获取产线"""
    if not product_name:
        return None
    for keyword, line in PRODUCT_TYPE_TO_LINE.items():
        if keyword in product_name:
            return line
    return None


def resolve_line(order_no: str = '', product_name: str = '') -> str:
    """综合解析产线"""
    line = get_line_by_order_no(order_no)
    if line:
        return line
    line = get_line_by_product(product_name)
    if line:
        return line
    return '默认产线'
