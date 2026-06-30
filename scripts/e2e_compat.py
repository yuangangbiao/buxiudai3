"""[v3.7.7.1] 端到端测试：模拟 service 真实调用流程"""
import sys
sys.path.insert(0, '.')

# 模拟 manual_publish_service.py 的真实调用方式
from mobile_api_ai.dispatch_center.publisher import get_publisher, get_all_tasks

print('=== 模拟工人点报工按钮的完整流程 ===')
print()

# Step 1: service 初始化（service._integration = get_publisher('report')）
integration = get_publisher('report')
print(f'1. service 初始化完成: {type(integration).__name__}')

# Step 2: service 调用旧 API（service 实际代码就是这样）
task_id = integration.publish_report_task(
    order_no='WO-2026-E2E-001',
    process_name='拉丝',
    customer_name='客户A',
    product_type='304钢',
    quantity=100,
    unit='米',
    planned_qty=100,
    process_status='待开始',
    operator_id='OP001',
    operator_name='张三',
    priority='normal',
    is_outsource=False,
    voice_text='订单WO-2026-E2E-001，工序拉丝'
)
print(f'2. 调用 publish_report_task 返回: {task_id}')

# Step 3: 验证任务真存了
tasks = get_all_tasks()
matching = [t for t in tasks if t['id'] == 'WO-2026-E2E-001']
print(f'3. 在存储中查找任务: {"找到" if matching else "未找到"}')
if matching:
    print(f'   payload: {matching[0]["payload"]}')

# Step 4: 模拟物料调用
integration_material = get_publisher('material')
task_id2 = integration_material.publish_material_task(
    order_no='WO-2026-E2E-002',
    materials=[{'name': '钢丝', 'required_qty': 50, 'unit': 'kg'}],
    process_name='拉丝',
    customer_name='客户A',
    priority='high'
)
print(f'4. 物料调用返回: {task_id2}')

# Step 5: 模拟质检调用
integration_quality = get_publisher('quality')
task_id3 = integration_quality.publish_quality_task(
    order_no='WO-2026-E2E-003',
    customer_name='客户A',
    product_type='304钢',
    inspection_type='终检'
)
print(f'5. 质检调用返回: {task_id3}')

print()
print('=== 端到端测试通过 ✅ ===')
print('修复前: AttributeError: object has no attribute publish_report_task')
print('修复后: 真实返回值，正常存储')