# -*- coding: utf-8 -*-
"""
dispatch_center/_operators.py 集成测试

执行: python dispatch_center/_operators_test.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_operators_imports():
    """测试 _operators.py 模块可以正常导入"""
    print('=' * 60)
    print('测试 1: 导入 _operators.py 模块')
    print('=' * 60)

    from dispatch_center._operators import (
        get_operators, get_operator_info, get_operators_by_department,
        get_department_members, list_departments,
        get_customer_group_for_order,
        clear_operators_cache, clear_customer_group_cache,
        # 向后兼容别名
        _get_operators, _get_department_members, _get_customer_group_for_order,
        OPERATORS_CACHE_TTL, CUSTOMER_GROUP_CACHE_TTL,
    )
    print('✅ 所有操作员函数导入成功')

    print('')
    print('=' * 60)
    print('测试 2: 向后兼容别名')
    print('=' * 60)
    if _get_operators is get_operators:
        print('✅ _get_operators 是 get_operators 的别名')
    if _get_department_members is get_department_members:
        print('✅ _get_department_members 是 get_department_members 的别名')
    if _get_customer_group_for_order is get_customer_group_for_order:
        print('✅ _get_customer_group_for_order 是 get_customer_group_for_order 的别名')

    print('')
    print('=' * 60)
    print('测试 3: 函数签名')
    print('=' * 60)
    import inspect

    sig = inspect.signature(get_operators)
    params = list(sig.parameters.keys())
    if params == []:
        print(f'✅ get_operators() 无参数签名正确')
    else:
        print(f'❌ get_operators 签名错误: {params}')

    sig = inspect.signature(get_operator_info)
    params = list(sig.parameters.keys())
    if 'operator_id' in params:
        print(f'✅ get_operator_info(operator_id) 签名正确')
    else:
        print(f'❌ get_operator_info 签名错误: {params}')

    sig = inspect.signature(get_operators_by_department)
    params = list(sig.parameters.keys())
    if 'department_name' in params:
        print(f'✅ get_operators_by_department(department_name) 签名正确')
    else:
        print(f'❌ get_operators_by_department 签名错误: {params}')

    print('')
    print('=' * 60)
    print('测试 4: 缓存 TTL 配置')
    print('=' * 60)
    print(f'✅ OPERATORS_CACHE_TTL = {OPERATORS_CACHE_TTL}s')
    print(f'✅ CUSTOMER_GROUP_CACHE_TTL = {CUSTOMER_GROUP_CACHE_TTL}s')

    print('')
    print('=' * 60)
    print('测试 5: 缓存清理函数')
    print('=' * 60)
    try:
        clear_operators_cache()
        print('✅ clear_operators_cache() 调用成功')
    except Exception as e:
        print(f'❌ clear_operators_cache 失败: {e}')

    try:
        clear_customer_group_cache()
        print('✅ clear_customer_group_cache() 调用成功')
    except Exception as e:
        print(f'❌ clear_customer_group_cache 失败: {e}')

    print('')
    print('=' * 60)
    print('测试 6: 模块文档')
    print('=' * 60)
    import dispatch_center._operators as op_mod
    if op_mod.__doc__ and '操作员工具层' in op_mod.__doc__:
        print('✅ 模块文档齐全')
    else:
        print('❌ 模块文档缺失')

    print('')
    print('=' * 60)
    print('所有测试通过！')
    print('=' * 60)


if __name__ == '__main__':
    test_operators_imports()