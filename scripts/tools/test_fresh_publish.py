# -*- coding: utf-8 -*-
"""用全新订单号测试完整发布流程"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
os.environ['PYTHONIOENCODING'] = 'utf-8'

from config import CONTAINER_CENTER_URL
from services.schedule_dispatch_service import ScheduleDispatchService
from models.database import get_connection
import requests

# 使用全新订单号
wo_no = "WO-FRESH-TEST-" + os.urandom(4).hex()
order = {'order_no': 'ORD-FRESH-TEST-' + os.urandom(4).hex()}
prod_id = 99990

print(f"订单号: {wo_no}")
print(f"订单号: {order['order_no']}")
print()

# 1. 调用 publish_schedule（首次发布）
print(">>> 首次发布 <<<")
result1 = ScheduleDispatchService.publish_schedule(wo_no, order, prod_id, "", "")
print(f"  success={result1['success']}")
print(f"  message={result1['message']}")
print()

# 2. 再次调用（模拟重复点击）
print(">>> 再次发布（模拟重复点击） <<<")
result2 = ScheduleDispatchService.publish_schedule(wo_no, order, prod_id, "", "")
print(f"  success={result2['success']}")
print(f"  message={result2['message']}")
print()

# 3. 检查容器中心 API
check_url = f"{CONTAINER_CENTER_URL}/api/processes?search={wo_no}"
resp = requests.get(check_url, timeout=10)
data = resp.json()
records = data.get('data', [])
print(f">>> 容器中心查询: {len(records)} 条记录 <<<")
for r in records:
    print(f"  work_order_no={r.get('work_order_no')} order_no={r.get('order_no')}")
