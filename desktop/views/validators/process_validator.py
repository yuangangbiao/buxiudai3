# -*- coding: utf-8 -*-
"""工序报工校验器 — 从 process_view.py 提取"""
from typing import List, Tuple


def validate_report_submission(
    order_id: int,
    proc_name: str,
    qty: float,
    qualified: float,
    hours: float,
    has_production: bool,
    has_record: bool,
) -> Tuple[bool, List[str]]:
    """校验报工提交数据

    Returns:
        (is_valid, errors)
    """
    errors = []

    if not order_id:
        errors.append("请先选择一个订单")
    if not proc_name:
        errors.append("请选择要报工的工序")
    if not has_production:
        errors.append("该订单尚未排产")
    if not has_record:
        errors.append("未找到对应工序记录")

    # 数量验证
    if qty <= 0:
        errors.append("请输入报工数量")
    if hours < 0:
        errors.append("工时不能为负数")
    if qualified < 0:
        errors.append("合格数量不能为负数")

    is_valid = len(errors) == 0
    return is_valid, errors


def validate_process_input(
    process_name: str,
    process_seq: int,
    planned_qty: int,
    worker: str,
) -> Tuple[bool, List[str]]:
    """校验添加工序输入数据"""
    errors = []

    if not process_name or not process_name.strip():
        errors.append("请输入工序名称")
    if planned_qty <= 0:
        errors.append("计划数量必须大于0")
    if not worker or not worker.strip():
        errors.append("请填写负责人")
    if process_seq < 1:
        errors.append("工序序号必须大于0")

    is_valid = len(errors) == 0
    return is_valid, errors


def parse_numeric_inputs(qty_str: str, qualified_str: str = "0", hours_str: str = "0"):
    """解析报工数值输入，返回 (qty, qualified, hours, error_message)"""
    try:
        qty = float(qty_str or 0)
        qualified = float(qualified_str or 0)
        hours = float(hours_str or 0)
    except (ValueError, TypeError):
        return 0, 0, 0, "请输入有效数字"
    return qty, qualified, hours, None
