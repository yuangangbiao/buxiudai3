"""[分析] 服务调用 publisher 的方法"""
import os
import re

print('=== 服务的 _integration.xxx 调用 ===')
for svc in ['manual_publish_service.py', 'auto_publish_service.py',
            'container_event_listener.py', 'material_publish_service.py',
            'task_recall_service.py']:
    if not os.path.exists(svc):
        continue
    with open(svc, 'r', encoding='utf-8') as f:
        content = f.read()
    calls = set(re.findall(r'_integration\.(\w+)\(', content))
    if calls:
        print(f'  {svc}: {sorted(calls)}')

print()
print('=== publisher.py 实际提供的方法 ===')
print('  BasePublisher: publish, recall, is_available, get_circuit_breaker_status')
print('  ReportPublisher.publish - 接受 1 个 payload 参数')
print('  MaterialPublisher.publish - 接受 1 个 payload 参数')
print('  QualityPublisher.publish - 接受 1 个 payload 参数')
print('  TaskRecallPublisher.recall - 接受 1 个 task_id 参数')
print()
print('=== ⚠️ 不匹配警告 ===')
print('如果服务调用 publish_report_task(order_no=...) 但 publisher 只有 publish(payload)')
print('说明服务是直接调用 desktop_container_integration 的 publish_report_task！')
print()
print('验证 desktop_container_integration.py 是否被引用：')
import subprocess
for svc in ['manual_publish_service.py', 'auto_publish_service.py',
            'container_event_listener.py', 'material_publish_service.py',
            'task_recall_service.py']:
    with open(svc, 'r', encoding='utf-8') as f:
        content = f.read()
    if 'desktop_container_integration' in content:
        print(f'  ⚠️ {svc} 仍引用 desktop_container_integration')
    elif 'publish_report_task' in content:
        # 说明直接调用 .publish_report_task 而不是 .publish
        print(f'  ⚠️ {svc} 调用 .publish_report_task 但 publisher 只有 .publish(payload)')