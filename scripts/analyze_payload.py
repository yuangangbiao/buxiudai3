"""分析 payload 字段"""
import re

with open(r'mobile_api_ai\dispatch_center\publisher.py', 'r', encoding='utf-8') as f:
    pub = f.read()

# payload.get('xxx') 字段
field_pattern = re.compile(r"payload\.get\(['\"]([^'\"]+)['\"]")

fields = set()
for match in field_pattern.finditer(pub):
    fields.add(match.group(1))

print('=== payload 实际使用的字段 ===')
for f in sorted(fields):
    print(f'  {f}')

# 看 5 个 service 文件调用 publisher 时的 payload 构造
print()
print('=== 服务端调用 publisher.publish() 的例子 ===')
for svc in ['manual_publish_service.py', 'auto_publish_service.py',
            'container_event_listener.py', 'material_publish_service.py']:
    try:
        with open(svc, 'r', encoding='utf-8') as f:
            content = f.read()
        # 找 publisher.publish(...) 调用
        m = re.search(r'publish\(\{[^}]+\}\)', content)
        if m:
            print(f'  {svc}:')
            print(f'    {m.group(0)[:300]}')
    except Exception as e:
        pass

# 估算每条 payload 大小（看示例）
print()
print('=== Payload 估算 ===')
sample = {'order_no': 'WO-2026-001', 'process_name': '拉丝', 'quantity': 100,
          'unit': '米', 'operator': '张三', 'work_time': '2026-06-25T10:30:00'}
import json
sample_json = json.dumps(sample, ensure_ascii=False)
print(f'  单条 payload 大小: ~{len(sample_json.encode("utf-8"))} bytes (JSON)')
print(f'  单条含中文字段 ~ 200-500 bytes（含订单号+工序+数量+操作员等）')