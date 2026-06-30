# -*- coding: utf-8 -*-
"""
自动推进 current_step 判定函数 - 单测

实现方案 A：报工数达标即推 1 步
不依赖 Flask 路由和 MySQL，纯函数可测
"""
import sys
import os
import pytest

# 路径注入
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
_MOBILE_ROOT = os.path.join(_PROJECT_ROOT, 'mobile_api_ai')
for p in (_PROJECT_ROOT, _MOBILE_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from api.auto_advance import decide_auto_advance


# 7 步模板（7 个元素，索引 0~6，最后一步索引 6 是边界）
STEPS_7 = [
    {'name': '工单发布',  'status_key': 'published'},
    {'name': '排产制定',  'status_key': 'scheduled'},
    {'name': '排产确认',  'status_key': 'confirmed'},
    {'name': '生产执行',  'status_key': 'in_production'},
    {'name': '报工完成',  'status_key': 'reported'},
    {'name': '质检审核',  'status_key': 'qc_passed'},
    {'name': '完工入库',  'status_key': 'completed'},
]


def test_partial_reported_no_advance():
    """case 1: 报工数 < 需求量 → 不推进（current_step 不变）"""
    result = decide_auto_advance(
        order_no='WO-001',
        step_name='生产执行',
        order_quantity=1000,
        cumulative_qty=500,            # 未达标
        current_step=3,
        steps=STEPS_7,
    )
    assert result.should_advance is False
    assert result.from_step == 3
    assert result.to_step == 3
    assert result.reason == 'not_reached_required'


def test_full_reported_advance_one():
    """case 2: 报工数 ≥ 需求量 → 推 1 步（current_step 3 → 4）"""
    result = decide_auto_advance(
        order_no='WO-001',
        step_name='生产执行',
        order_quantity=1000,
        cumulative_qty=1000,           # ✅ 达标
        current_step=3,
        steps=STEPS_7,
    )
    assert result.should_advance is True
    assert result.from_step == 3
    assert result.to_step == 4
    assert result.reason == 'qty_reached'


def test_over_reported_advance_one_not_multi():
    """case 3: 报工数远超需求量（如 5000/1000）→ 只推 1 步，不跨多步"""
    result = decide_auto_advance(
        order_no='WO-001',
        step_name='生产执行',
        order_quantity=1000,
        cumulative_qty=5000,           # 远超达标
        current_step=3,
        steps=STEPS_7,
    )
    assert result.should_advance is True
    assert result.from_step == 3
    assert result.to_step == 4           # ✅ 只 +1，不 +2 / +3
    assert result.reason == 'qty_reached'


def test_at_last_step_no_advance():
    """case 4: current_step 已在最后一步 → 不推进（防止越界）"""
    result = decide_auto_advance(
        order_no='WO-001',
        step_name='完工入库',
        order_quantity=1000,
        cumulative_qty=1000,           # 达标
        current_step=6,                # ✅ 已经是最后一步
        steps=STEPS_7,
    )
    assert result.should_advance is False
    assert result.to_step == 6           # 保持不变
    assert result.reason == 'at_max_step'


def test_current_step_ahead_no_advance():
    """case 5: current_step 已超过该工序索引（已被其他人推进）→ 不动"""
    # 假设已经 current_step=5（质检），现在报"生产执行"——current_step 早就过这步了
    result = decide_auto_advance(
        order_no='WO-001',
        step_name='生产执行',
        order_quantity=1000,
        cumulative_qty=1000,
        current_step=5,                # 已超过 step 3
        steps=STEPS_7,
    )
    assert result.should_advance is False
    assert result.reason == 'current_step_ahead'


def test_zero_order_qty_no_advance():
    """case 6: 订单数量 = 0（异常）→ 不推进"""
    result = decide_auto_advance(
        order_no='WO-001',
        step_name='生产执行',
        order_quantity=0,              # 异常
        cumulative_qty=1000,
        current_step=3,
        steps=STEPS_7,
    )
    assert result.should_advance is False
    assert result.reason == 'invalid_order_qty'


def test_empty_steps_no_advance():
    """case 7: 工序 steps 为空 → 不推进（兜底）"""
    result = decide_auto_advance(
        order_no='WO-001',
        step_name='生产执行',
        order_quantity=1000,
        cumulative_qty=1000,
        current_step=3,
        steps=[],
    )
    assert result.should_advance is False
    assert result.reason == 'no_steps'


if __name__ == '__main__':
    test_partial_reported_no_advance()
    test_full_reported_advance_one()
    test_over_reported_advance_one_not_multi()
    test_at_last_step_no_advance()
    test_current_step_ahead_no_advance()
    test_zero_order_qty_no_advance()
    test_empty_steps_no_advance()
    print('✓ 7 个 case 全部通过')
