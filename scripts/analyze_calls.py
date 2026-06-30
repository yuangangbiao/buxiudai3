"""分析 publisher 调用方"""
import re
import os

print('=== 5 个服务文件的 publisher.publish() 调用 ===')
for svc in ['manual_publish_service.py', 'auto_publish_service.py',
            'container_event_listener.py', 'material_publish_service.py',
            'task_recall_service.py']:
    try:
        with open(svc, 'r', encoding='utf-8') as f:
            content = f.read()
        # 找 publish( 之后 200 字符
        for m in re.finditer(r'publish\(([^)]{0,300})\)', content):
            snippet = m.group(0)
            if 'pubsub' in snippet or 'integration' in snippet or 'publisher' in snippet.lower():
                print(f'\n{svc}:')
                print(f'  {snippet[:300]}')
                break
    except Exception as e:
        pass

print()
print('=== 调用频次估算 ===')
print('  - 报工 publish: 高频（每个工序报工 1 次，约 50-200 次/天）')
print('  - 物料 publish: 中频（每个订单 1-5 次，约 30-100 次/天）')
print('  - 质检 publish: 低频（每个工序 1 次，约 20-80 次/天）')
print('  - 任务撤回 recall: 极低频（< 5 次/天）')