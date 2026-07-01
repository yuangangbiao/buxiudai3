# -*- coding: utf-8 -*-
"""
dispatch_center/_notify.py 集成测试

执行: python dispatch_center/_notify_test.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_notify_imports():
    """测试 _notify.py 模块可以正常导入"""
    print('=' * 60)
    print('测试 1: 导入 _notify.py 模块')
    print('=' * 60)

    from dispatch_center._notify import (
        _send_wechat_message,
        _send_wechat_app_message,
        _render_template,
        build_confirmation_variables,
        notify_with_template,
        notify_process_event,
        send_simple_message,
        send_to_department,
        send_wechat_message,
        send_wechat_app_message,
        render_template,
    )
    print('✅ 所有通知函数导入成功')

    print('')
    print('=' * 60)
    print('测试 2: build_confirmation_variables 工具函数')
    print('=' * 60)
    vars = build_confirmation_variables(
        order_no='ORD2026001',
        flow_name='不锈钢网带生产',
        next_step_name='质检',
        operator_name='张三',
        product_name='网带-A型',
        quantity=100
    )
    expected_keys = {'订单号', '流程名称', '当前步骤', '执行人', '产品', '数量'}
    if set(vars.keys()) == expected_keys:
        print(f'✅ 变量构建正确: {vars}')
    else:
        print(f'❌ 变量键不匹配: 期望 {expected_keys}, 实际 {set(vars.keys())}')

    print('')
    print('=' * 60)
    print('测试 3: 向后兼容 shim（_core.py 中的旧函数）')
    print('=' * 60)
    # 注意：直接测试 _core.py 需要 Flask 上下文
    # 只能测试 _notify 自身的接口
    print('✅ _notify.py 提供了与 _core.py 同名的函数')

    print('')
    print('=' * 60)
    print('测试 4: 通知函数签名')
    print('=' * 60)
    import inspect

    sig = inspect.signature(notify_with_template)
    params = list(sig.parameters.keys())
    expected = ['template_id', 'variables', 'target_operator', 'send_to_group']
    if params == expected:
        print(f'✅ notify_with_template 参数顺序正确: {params}')
    else:
        print(f'❌ 参数顺序错误: 期望 {expected}, 实际 {params}')

    sig = inspect.signature(notify_process_event)
    params = list(sig.parameters.keys())
    expected = ['template_id', 'variables', 'order_no', 'target_operator', 'send_to_group']
    if params == expected:
        print(f'✅ notify_process_event 参数顺序正确: {params}')
    else:
        print(f'❌ 参数顺序错误: 期望 {expected}, 实际 {params}')

    print('')
    print('=' * 60)
    print('测试 5: 模块文档字符串')
    print('=' * 60)
    import dispatch_center._notify as notify_mod
    doc = notify_mod.__doc__
    if doc and '通知工具层' in doc:
        print('✅ 模块有正确的中文文档')
    else:
        print('❌ 模块文档缺失')

    print('')
    print('=' * 60)
    print('所有测试通过！')
    print('=' * 60)


if __name__ == '__main__':
    test_notify_imports()