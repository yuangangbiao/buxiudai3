"""[v3.7.7.1] 验证兼容层 API 调用

确保 service 文件调用旧 API 不会 AttributeError
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))


def test_report_publisher_compat_api():
    """publish_report_task 兼容旧签名"""
    from mobile_api_ai.dispatch_center.publisher import get_publisher
    p = get_publisher('report')

    # service 调用的方式
    result = p.publish_report_task(
        order_no='WO-2026-001',
        process_name='拉丝',
        customer_name='客户A',
        product_type='304钢',
        quantity=100,
        unit='米',
        planned_qty=100,
        operator_id='OP001',
        operator_name='张三',
        priority='normal'
    )
    assert result == 'WO-2026-001', f'期望 WO-2026-001, 实际 {result}'
    print('✅ report publisher 兼容 API 通过')


def test_material_publisher_compat_api():
    """publish_material_task 兼容旧签名"""
    from mobile_api_ai.dispatch_center.publisher import get_publisher
    p = get_publisher('material')

    result = p.publish_material_task(
        order_no='WO-2026-002',
        materials=[{'name': '钢丝', 'qty': 50}],
        process_name='拉丝',
        customer_name='客户A',
        priority='normal'
    )
    assert result == 'WO-2026-002'
    print('✅ material publisher 兼容 API 通过')


def test_quality_publisher_compat_api():
    """publish_quality_task 兼容旧签名"""
    from mobile_api_ai.dispatch_center.publisher import get_publisher
    p = get_publisher('quality')

    result = p.publish_quality_task(
        order_no='WO-2026-003',
        customer_name='客户A',
        product_type='304钢',
        inspection_type='终检'
    )
    assert result == 'WO-2026-003'
    print('✅ quality publisher 兼容 API 通过')


def test_new_api_still_works():
    """新 publish(payload) API 仍然可用"""
    from mobile_api_ai.dispatch_center.publisher import get_publisher
    p = get_publisher('report')

    result = p.publish({
        'order_no': 'WO-2026-004',
        'process_name': '拉丝',
    })
    assert result is True
    print('✅ 新 publish(payload) API 仍可用')


def test_kwargs_pass_through():
    """**kwargs 透传到 payload"""
    from mobile_api_ai.dispatch_center.publisher import get_publisher
    p = get_publisher('report')

    p.publish_report_task(
        order_no='WO-2026-005',
        process_name='拉丝',
        extra_field='扩展字段',
        custom_remark='特殊备注'
    )
    # 通过 get_all_tasks 验证存储
    from mobile_api_ai.dispatch_center.publisher import get_all_tasks
    tasks = get_all_tasks()
    matching = [t for t in tasks if t['id'] == 'WO-2026-005']
    assert len(matching) == 1
    assert matching[0]['payload']['extra_field'] == '扩展字段'
    assert matching[0]['payload']['custom_remark'] == '特殊备注'
    print('✅ **kwargs 透传通过')


if __name__ == '__main__':
    test_report_publisher_compat_api()
    test_material_publisher_compat_api()
    test_quality_publisher_compat_api()
    test_new_api_still_works()
    test_kwargs_pass_through()
    print('\n=== 全部 5 个兼容层测试通过 ===')