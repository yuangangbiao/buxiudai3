# -*- coding: utf-8 -*-
"""调试排产发布流程"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
os.environ['PYTHONIOENCODING'] = 'utf-8'

from config import CONTAINER_CENTER_URL
print(f'CONTAINER_CENTER_URL = {CONTAINER_CENTER_URL}')

# 1. 测试直接调用容器中心 API
import requests, json
url = f'{CONTAINER_CENTER_URL}/api/schedule/publish'
payload = {
    'work_order_no': 'WO-DEBUG-001',
    'order_no': 'ORD-DEBUG-001',
    'prod_id': 1,
    'source': 'main_software',
}
print(f'\n1. 直接 POST {url}')
try:
    resp = requests.post(url, json=payload, timeout=15)
    print(f'   HTTP {resp.status_code}')
    print(f'   返回: {resp.json()}')
except Exception as e:
    print(f'   ERROR: {e}')

# 2. 测试 ScheduleDispatchService.publish_schedule
from services.schedule_dispatch_service import ScheduleDispatchService
print(f'\n2. ScheduleDispatchService.publish_schedule()')
order = {'order_no': 'ORD-DEBUG-001', 'customer_group': '调试客户', 'product_type': '不锈钢网'}
try:
    r = ScheduleDispatchService.publish_schedule('WO-DEBUG-002', order, 2, '', '')
    print(f'   Result: {r}')
except Exception as e:
    import traceback
    print(f'   ERROR: {e}')
    traceback.print_exc()
