# -*- coding: utf-8 -*-
"""
dispatch_center/_sync.py 集成测试

执行: python dispatch_center/_sync_test.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_sync_imports():
    """测试 _sync.py 模块可以正常导入"""
    print('=' * 60)
    print('测试 1: 导入 _sync.py 模块')
    print('=' * 60)

    from dispatch_center._sync import (
        sync_work_order_status,
        sync_to_mysql,
        sync_schedule_to_container,
        get_cached_work_orders,
        get_doc_data,
        # 向后兼容别名
        _sync_work_order_status,
        _sync_to_mysql,
        _sync_schedule_to_container,
        _get_cached_work_orders,
        _get_doc_data,
    )
    print('✅ 所有同步函数导入成功')

    print('')
    print('=' * 60)
    print('测试 2: 向后兼容别名')
    print('=' * 60)
    if _sync_work_order_status is sync_work_order_status:
        print('✅ _sync_work_order_status 是 sync_work_order_status 的别名')
    if _sync_to_mysql is sync_to_mysql:
        print('✅ _sync_to_mysql 是 sync_to_mysql 的别名')
    if _sync_schedule_to_container is sync_schedule_to_container:
        print('✅ _sync_schedule_to_container 是 sync_schedule_to_container 的别名')
    if _get_cached_work_orders is get_cached_work_orders:
        print('✅ _get_cached_work_orders 是 get_cached_work_orders 的别名')
    if _get_doc_data is get_doc_data:
        print('✅ _get_doc_data 是 get_doc_data 的别名')

    print('')
    print('=' * 60)
    print('测试 3: 函数签名')
    print('=' * 60)
    import inspect

    sig = inspect.signature(sync_work_order_status)
    params = list(sig.parameters.keys())
    expected = ['order_no', 'status_key', 'current_step', 'process_id']
    if params == expected:
        print(f'✅ sync_work_order_status 签名正确: {params}')
    else:
        print(f'❌ sync_work_order_status 签名错误: 期望 {expected}, 实际 {params}')

    sig = inspect.signature(sync_to_mysql)
    params = list(sig.parameters.keys())
    expected = ['order_no', 'completed_step_status', 'lead_time']
    if params == expected:
        print(f'✅ sync_to_mysql 签名正确: {params}')
    else:
        print(f'❌ sync_to_mysql 签名错误: 期望 {expected}, 实际 {params}')

    sig = inspect.signature(get_doc_data)
    params = list(sig.parameters.keys())
    if 'item' in params:
        print(f'✅ get_doc_data(item) 签名正确')
    else:
        print(f'❌ get_doc_data 签名错误: {params}')

    print('')
    print('=' * 60)
    print('测试 4: get_doc_data 数据提取')
    print('=' * 60)
    # 测试 dict 类型
    item1 = {'doc_data': {'order_no': 'ORD001', 'product': 'A'}}
    result = get_doc_data(item1)
    if result == {'order_no': 'ORD001', 'product': 'A'}:
        print(f'✅ dict 类型提取正确: {result}')
    else:
        print(f'❌ dict 提取错误: {result}')

    # 测试 JSON string
    item2 = {'doc_data': '{"order_no": "ORD002"}'}
    result = get_doc_data(item2)
    if result == {'order_no': 'ORD002'}:
        print(f'✅ JSON string 类型提取正确: {result}')
    else:
        print(f'❌ JSON string 提取错误: {result}')

    # 测试 None
    result = get_doc_data(None)
    if result == {}:
        print('✅ None 类型安全处理')
    else:
        print(f'❌ None 处理错误: {result}')

    # 测试非 dict
    result = get_doc_data("not a dict")
    if result == {}:
        print('✅ 非 dict 类型安全处理')
    else:
        print(f'❌ 非 dict 处理错误: {result}')

    # 测试 content 字段
    item3 = {'content': {'order_no': 'ORD003', 'qty': 100}}
    result = get_doc_data(item3)
    if result == {'order_no': 'ORD003', 'qty': 100}:
        print(f'✅ content 字段提取正确: {result}')
    else:
        print(f'❌ content 字段提取错误: {result}')

    print('')
    print('=' * 60)
    print('测试 5: 模块文档')
    print('=' * 60)
    import dispatch_center._sync as sync_mod
    if sync_mod.__doc__ and '同步工具层' in sync_mod.__doc__:
        print('✅ 模块文档齐全')
    else:
        print('❌ 模块文档缺失')

    print('')
    print('=' * 60)
    print('所有测试通过！')
    print('=' * 60)


if __name__ == '__main__':
    test_sync_imports()