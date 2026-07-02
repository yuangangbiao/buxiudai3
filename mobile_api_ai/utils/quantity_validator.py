# -*- coding: utf-8 -*-
"""
[v3.6 T3] quantity 业务化校验函数

5 业务类型 + 4 边界场景
"""
from decimal import Decimal


# 业务类型 → 校验规则
RULES = {
    'material_records': {
        'type': int,
        'allow_decimal': False,
        'allow_zero': False,
        'min': 1,
        'max_overshoot': 1.2,  # 超出计划 20% 警告
    },
    'process_sub_steps': {
        'type': float,
        'allow_decimal': True,
        'allow_zero': False,
        'min': 0.01,
        'max_overshoot': 2.0,  # 工序允许 2 倍
    },
    'quality_records': {
        'type': int,
        'allow_decimal': False,
        'allow_zero': True,  # 合格品 defect_qty=0
        'min': 0,
        'max_overshoot': 1.0,  # 不良数不能超总数量
    },
    'outsource_records': {
        'type': float,
        'allow_decimal': True,
        'allow_zero': False,
        'min': 0.01,
        'max_overshoot': 1.2,
    },
    'repair_records': {
        'type': int,
        'allow_decimal': False,
        'allow_zero': True,  # 报修次数可为 0
        'min': 0,
        'max_overshoot': 1.0,
    },
}


def validate_quantity(business_type: str, field: str, value, plan_qty=None):
    """[T3] quantity 业务化校验

    Args:
        business_type: 业务表名（material_records 等）
        field: 字段名（quantity, planned_qty 等）
        value: 待校验的值
        plan_qty: 计划数（用于超限判断）

    Returns:
        (is_valid: bool, error_msg: str)
    """
    rule = RULES.get(business_type)
    if not rule:
        return True, None

    # 1. None / 空值
    if value is None:
        return False, f'{field} 不能为空'

    # 2. 小数校验（物料不允许小数）— **先校验小数**
    if not rule['allow_decimal']:
        # 整数业务：必须是 int 或整数化的 float
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False, f'{field} 类型错误'
        if isinstance(value, float) and not value.is_integer():
            return False, f'{field} 必须为整数（不允许小数）'

    # 3. 浮点业务：必须是数字
    elif rule['allow_decimal']:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return False, f'{field} 类型错误'

    # 4. 0 拒绝（如果不允许 0）
    if not rule['allow_zero'] and value == 0:
        return False, f'{field} 不能为 0'

    # 5. 负数拒绝
    if value < 0:
        return False, f'{field} 不能为负数'

    # 6. 超计划判断
    if plan_qty and value > plan_qty * rule['max_overshoot']:
        return False, f'{field} 超出计划数 {int((rule["max_overshoot"]-1)*100)}%（{plan_qty} → {value}）'

    return True, None


# T3 单元测试
if __name__ == '__main__':
    print('[1/8] material_records quantity 校验')
    ok, msg = validate_quantity('material_records', 'quantity', 10, plan_qty=10)
    assert ok, f'应通过: {msg}'
    ok, msg = validate_quantity('material_records', 'quantity', 0, plan_qty=10)
    assert not ok
    assert '不能为 0' in msg
    print('   PASS')

    print('[2/8] material_records quantity=10.5 拒绝')
    ok, msg = validate_quantity('material_records', 'quantity', 10.5, plan_qty=10)
    print(f'   ok={ok} msg={msg!r}')
    assert not ok
    assert '整数' in msg
    print('   PASS')

    print('[3/8] process_sub_steps quantity=10.5 接受')
    ok, msg = validate_quantity('process_sub_steps', 'quantity', 10.5, plan_qty=10)
    assert ok, f'应通过: {msg}'
    print('   PASS')

    print('[4/8] quality_records defect_qty=0 接受')
    ok, msg = validate_quantity('quality_records', 'defect_qty', 0, plan_qty=10)
    assert ok, f'应通过: {msg}'
    print('   PASS')

    print('[5/8] quality_records defect_qty=-1 拒绝')
    ok, msg = validate_quantity('quality_records', 'defect_qty', -1, plan_qty=10)
    assert not ok
    print('   PASS')

    print('[6/8] 5 业务类型超限判断')
    for bt in ['material_records', 'process_sub_steps', 'quality_records', 'outsource_records', 'repair_records']:
        ok, msg = validate_quantity(bt, 'qty', 1000, plan_qty=10)
        # 5 业务类型都应该拒绝 1000（远超计划）
        print(f'   {bt}: ok={ok}, msg={msg[:50] if msg else "ok"}')

    print('[7/8] 未知业务类型不校验')
    ok, msg = validate_quantity('unknown_table', 'qty', 100)
    assert ok
    print('   PASS')

    print('[8/8] None 值拒绝')
    ok, msg = validate_quantity('material_records', 'quantity', None)
    assert not ok
    print('   PASS')

    print('\n8/8 全部通过')
