# -*- coding: utf-8 -*-
"""回归决策树 — 纯函数，无副作用"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple

# 动作常量
INSERT = 'insert'
OVERWRITE = 'overwrite'
PROMPT = 'prompt'
IDEMPOTENT = 'idempotent'
REJECT_TIMEOUT = 'reject_timeout'
REJECT_OVER_QTY = 'reject_over_qty'
REJECT_LOCKED = 'reject_locked'

REGRESSION_ACTIONS = {
    INSERT, OVERWRITE, PROMPT, IDEMPOTENT,
    REJECT_TIMEOUT, REJECT_OVER_QTY, REJECT_LOCKED,
}

# 时限常量
GRACE_MINUTES = 30          # 自由修正期
AUDIT_HOURS = 24             # 审核修正期
MALICIOUS_THRESHOLD = 3      # 24h 内恶意覆盖上限
RETRY_LIMIT = 3              # 回归质检死循环上限


def decide_regression(
    operator: str,
    quantity: float,
    batch_no: str,
    existing: Optional[Dict],
    order_required_qty: float,
    regression_count_24h: int = 0,
    qc_locked: bool = False,
    qc_retry_count: int = 0,
) -> Tuple[str, Dict]:
    """回归决策核心函数。

    Args:
        operator: 当前操作员
        quantity: 本次报工数量
        batch_no: 批次号
        existing: 已有子步骤记录（None=首次报工）
        order_required_qty: 订单需求总量
        regression_count_24h: 24h内该操作员覆盖他人次数
        qc_locked: 订单是否被质检锁定
        qc_retry_count: 回归→质检循环轮次

    Returns:
        (action, context)
        action: 'insert'|'overwrite'|'prompt'|'idempotent'|'reject_*'
        context: dict 含理由/提示信息/弹窗数据
    """
    # ---- 锁检查 ----
    if qc_locked:
        return REJECT_LOCKED, {
            'message': '该订单正在质检中，数据已锁定',
            'reason': 'qc_locked',
        }

    # ---- 首次报工 ----
    if existing is None:
        return INSERT, {}

    # ---- 幂等检查 ----
    existing_batch = existing.get('batch_no', '')
    if (existing_batch == batch_no and
            float(existing.get('quantity', 0) or 0) == quantity and
            existing.get('operator', '') == operator):
        return IDEMPOTENT, {
            'existing_id': existing.get('id'),
            'message': '该批次已报工',
        }

    # ---- 修正时限判断 ----
    existing_created = existing.get('first_created_at') or existing.get('created_at')
    if existing_created and isinstance(existing_created, str):
        try:
            existing_created = datetime.fromisoformat(existing_created)
        except ValueError:
            existing_created = None

    now = datetime.now()
    if existing_created and isinstance(existing_created, datetime):
        age = now - existing_created
        if age > timedelta(hours=AUDIT_HOURS):
            return REJECT_TIMEOUT, {
                'message': '该记录已超过修正期限(24h)，请联系管理员',
                'reason': 'timeout',
            }
        is_grace = age <= timedelta(minutes=GRACE_MINUTES)
    else:
        is_grace = True  # 无时间戳时宽松处理

    # ---- 同人 vs 异人 ----
    same_operator = (existing.get('operator', '') == operator)
    old_qty = float(existing.get('quantity', 0) or 0)

    if same_operator:
        # ---- 同人同批次 → 幂等；无批次或不同批 → 允许分批报工 ----
        if batch_no and existing.get('batch_no') == batch_no:
            return IDEMPOTENT, {
                'existing_id': existing.get('id'),
                'message': '该批次已报工',
            }
        # 无批次号或不同批次 → 直接追加新记录
        return INSERT, {}

    # ---- 异人 ----
    # 恶意检测
    if regression_count_24h >= MALICIOUS_THRESHOLD:
        return REJECT_LOCKED, {
            'message': '24h 内覆盖他人超过 3 次，报工权限已冻结',
            'reason': 'malicious',
        }

    # 死循环检测
    if qc_retry_count >= RETRY_LIMIT:
        return REJECT_LOCKED, {
            'message': '该订单已进入 3 轮回归→质检循环，需管理员处理',
            'reason': 'retry_limit',
        }

    # 追加上限校验
    merged = old_qty + quantity
    if merged > order_required_qty:
        return REJECT_OVER_QTY, {
            'message': f'合并后({merged})超出需求({order_required_qty})',
            'reason': 'over_qty',
            'old_qty': old_qty,
            'new_qty': quantity,
            'merged': merged,
            'required': order_required_qty,
        }

    # 弹窗确认
    existing_op = existing.get('operator', '?')
    existing_time = str(existing.get('created_at', ''))[:16] if existing.get('created_at') else '未知'

    if quantity > old_qty:
        prompt_type = 'append'
        msg = f'{existing_op} 已于 {existing_time} 报工 {old_qty}，追加到 {merged}？'
    else:
        prompt_type = 'override_less'
        msg = f'{existing_op} 已于 {existing_time} 报工 {old_qty}，覆盖为 {quantity}？'

    return PROMPT, {
        'prompt_type': prompt_type,
        'message': msg,
        'existing_operator': existing_op,
        'existing_time': existing_time,
        'existing_id': existing.get('id'),
        'old_qty': old_qty,
        'new_qty': quantity,
        'merged': merged,
        'reason': 'other_override',
        'needs_qc': True,
    }
