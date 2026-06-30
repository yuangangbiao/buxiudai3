# -*- coding: utf-8 -*-
"""精确模拟 production_view 的 do_publish 流程"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['INVENTORY_API_KEY'] = 'test'  # 避免环境变量警告

import requests
from config import CONTAINER_CENTER_URL
from services.schedule_dispatch_service import ScheduleDispatchService
from models.production import ProductionDAO
from models.order import OrderDAO
from utils.op_logger import log_ui

# 使用一个测试订单号
wo_no = "WO-TEST-PUBLISH-001"
prod_id = 99999

print("=" * 60)
print("第一步：模拟 do_publish 中的已发布检查")
print("=" * 60)

check_url = f"{CONTAINER_CENTER_URL}/api/processes?search={wo_no}"
print(f"查询: GET {check_url}")
try:
    check_resp = requests.get(check_url, timeout=10)
    if check_resp.status_code == 200:
        check_data = check_resp.json()
        print(f"返回: {check_data}")
        records = check_data.get('data', []) if isinstance(check_data, dict) else []
        print(f"记录数: {len(records)}")
        if records and any(r.get('work_order_no') == wo_no for r in records):
            print(">>> 结论: 已发布，无需重复提交 <<<")
        else:
            print(">>> 结论: 未发布，可以继续 <<<")
    else:
        print(f"HTTP {check_resp.status_code}: {check_resp.text[:200]}")
        print(">>> 结论: 接口异常，跳过检查 <<<")
except requests.exceptions.ConnectionError:
    print(">>> 结论: 容器中心不可达，跳过检查 <<<")
except Exception as e:
    print(f">>> 结论: 检查异常: {e}，跳过 <<<")

print()
print("=" * 60)
print("第二步：模拟 publish_schedule 调用")
print("=" * 60)

order = {'order_no': 'ORD-TEST-PUBLISH-001'}
try:
    result = ScheduleDispatchService.publish_schedule(wo_no, order, prod_id, "", "")
    print(f"返回: success={result['success']}, message={result['message']}")
except Exception as e:
    import traceback
    print(f"异常: {e}")
    traceback.print_exc()

print()
print("=" * 60)
print("第三步：再次检查是否已发布 (模拟第二次点击)")
print("=" * 60)

try:
    check_resp2 = requests.get(check_url, timeout=10)
    if check_resp2.status_code == 200:
        check_data2 = check_resp2.json()
        records2 = check_data2.get('data', []) if isinstance(check_data2, dict) else []
        print(f"记录数: {len(records2)}")
        if records2 and any(r.get('work_order_no') == wo_no for r in records2):
            print(">>> 结论: 已发布，无需重复提交 <<<")
        else:
            print(">>> 结论: 未发布，可以继续 <<<")
except Exception as e:
    print(f"检查异常: {e}")
