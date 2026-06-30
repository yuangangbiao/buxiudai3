"""[验证] 运行时调用"""
import sys
sys.path.insert(0, '.')

from mobile_api_ai.dispatch_center.publisher import get_publisher

p = get_publisher('report')
print('publisher type:', type(p).__name__)
print('has publish_report_task:', hasattr(p, 'publish_report_task'))
print('has publish:', hasattr(p, 'publish'))

# 模拟 manual_publish_service.py 的调用
try:
    result = p.publish_report_task(
        order_no='WO-001',
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
    print('result:', result)
except AttributeError as e:
    print('AttributeError:', e)
except Exception as e:
    print(type(e).__name__, ':', e)