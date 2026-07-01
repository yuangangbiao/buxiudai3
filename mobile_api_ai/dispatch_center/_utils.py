# -*- coding: utf-8 -*-
"""Dispatch Center 工具函数

v1.0 (2026-06-22) — 由悲观审计沉淀的模式级修复抽出
"""
import logging

logger = logging.getLogger(__name__)


def safe_int(value, default=0, min_val=None, max_val=None):
    """安全地转换 request.args 值为 int

    Args:
        value: 来自 request.args.get() 的字符串值 (可能为 None 或非数字)
        default: 转换失败时返回的默认值
        min_val: 最小值边界 (None 表示不限制)
        max_val: 最大值边界 (None 表示不限制)

    Returns:
        int: 安全转换后的整数

    Examples:
        safe_int('abc') -> 0
        safe_int('abc', default=10) -> 10
        safe_int('5', default=0) -> 5
        safe_int('99999999', min_val=0, max_val=1000) -> 1000
        safe_int('-5', min_val=0) -> 0
        safe_int(None, default=10) -> 10

    Note:
        这是悲观审计经验池模式 #2 的标准实现，所有 int(request.args...) 必须改用此函数
    """
    try:
        result = int(value) if value is not None else default
    except (TypeError, ValueError):
        result = default

    if min_val is not None and result < min_val:
        result = min_val
    if max_val is not None and result > max_val:
        result = max_val

    return result


def safe_str(value, default='', max_length=None):
    """安全地获取 request.args 字符串值 (去除首尾空格)"""
    if value is None:
        result = default
    else:
        result = str(value).strip()
        if not result:
            result = default

    if max_length is not None and len(result) > max_length:
        result = result[:max_length]

    return result
