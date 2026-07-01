# -*- coding: utf-8 -*-
"""
自动推进 current_step 判定函数

方案 A：报工数达标即推 1 步
- 不依赖 Flask / MySQL，纯函数可单测
- 业务规则：
  1. 报工数 < 需求量 → 不推进
  2. 报工数 ≥ 需求量 + current_step < len(steps)-1 → 推 1 步（不跨多步）
  3. current_step >= len(steps)-1 → 已是最后一步，不再推
  4. current_step 已超过该工序索引 → 不动
  5. 订单数量 = 0 / 工序 steps 为空 → 兜底跳过

调用方：
    result = decide_auto_advance(...)
    if result.should_advance:
        UPDATE process_records SET current_step = result.to_step
        WHERE order_no = ? AND current_step = result.from_step  -- 并发保护
"""
from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class AdvanceDecision:
    should_advance: bool
    from_step: int
    to_step: int
    reason: str           # 用于日志/排查


def decide_auto_advance(
    order_no: str,
    step_name: str,
    order_quantity: float,
    cumulative_qty: float,
    current_step: int,
    steps: List[Dict],
) -> AdvanceDecision:
    """判定是否推进 current_step，返回决策结果。

    参数:
        order_no: 订单号（仅用于日志）
        step_name: 当前报工工序名（仅用于日志）
        order_quantity: 订单总需求量
        cumulative_qty: 该工序累计已报工数
        current_step: process_records.current_step 索引（0-based）
        steps: 工序定义列表（来自 process_records.steps JSON）

    返回:
        AdvanceDecision，包含 should_advance/from_step/to_step/reason
    """
    # 边界兜底
    if not steps or not isinstance(steps, list):
        return AdvanceDecision(False, current_step, current_step, 'no_steps')
    if order_quantity <= 0:
        return AdvanceDecision(False, current_step, current_step, 'invalid_order_qty')
    if current_step < 0:
        return AdvanceDecision(False, current_step, current_step, 'invalid_current_step')

    steps_len = len(steps)
    max_step = steps_len - 1

    # 已在最后一步 → 不推
    if current_step >= max_step:
        return AdvanceDecision(False, current_step, current_step, 'at_max_step')

    # 报工数未达标 → 不推
    if cumulative_qty < order_quantity:
        return AdvanceDecision(False, current_step, current_step, 'not_reached_required')

    # 报工数已达标 → 推 1 步
    # 防御性检查：current_step 已超该工序索引（其他流程已推），不动
    # 这种情况下 current_step 应该是 ≥ current_step 自身（恒真），所以加 steps[cur_step] name 比较
    cur_step_def = steps[current_step] if current_step < steps_len else None
    cur_step_name = cur_step_def.get('name', '') if isinstance(cur_step_def, dict) else str(cur_step_def or '')
    # 如果 current_step 已过 step_name 所在索引（例如 step_name='生产执行' 但 current_step=5 质检），
    # 则 cur_step_name != step_name，视为"已被推进"
    if step_name and cur_step_name and step_name != cur_step_name:
        return AdvanceDecision(False, current_step, current_step, 'current_step_ahead')

    return AdvanceDecision(True, current_step, current_step + 1, 'qty_reached')
