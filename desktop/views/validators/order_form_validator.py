# -*- coding: utf-8 -*-
"""订单表单校验器 — 从 new_order_dialog.py 提取"""
from typing import List, Tuple, Dict, Any


def validate_order_form(data: Dict[str, Any], dim_fields: List[Dict] = None) -> Tuple[bool, List[str]]:
    """校验订单表单数据

    Args:
        data: 表单收集的数据字典
        dim_fields: 尺寸参数字段定义列表，用于必填项校验

    Returns:
        (is_valid, errors): 校验通过标志 + 错误信息列表
    """
    errors = []

    # 必填项
    if not data.get("customer_name", "").strip():
        errors.append("请填写客户名称")
    if not data.get("product_type", "").strip():
        errors.append("请选择产品类型")

    # 数量验证
    try:
        qty = float(data.get("quantity", 0))
        if qty <= 0:
            errors.append("数量必须大于0")
    except (ValueError, TypeError):
        errors.append("数量请填写数字")

    # 单价验证（可选）
    unit_price = data.get("unit_price", "")
    if unit_price:
        try:
            price = float(unit_price)
            if price < 0:
                errors.append("单价不能为负数")
        except ValueError:
            errors.append("单价请填写数字")

    # 尺寸参数必填项
    if dim_fields:
        field_info = {fd["key"]: fd for fd in dim_fields}
        for key in data:
            fd = field_info.get(key, {})
            if fd.get("required") and not data.get(key, "").strip():
                label = fd.get("label", key)
                errors.append(f"「{label}」不能为空")

    is_valid = len(errors) == 0
    return is_valid, errors
