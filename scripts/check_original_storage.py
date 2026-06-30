"""[调查] 原始 desktop_container_integration.py 怎么存"""
import re

with open(r'desktop_container_integration.py', 'r', encoding='utf-8') as f:
    content = f.read()

print('=== 查找内存字典/列表定义（任务存储）===')
for m in re.finditer(r'self\.(\w+)\s*=\s*[\[\{]', content):
    attr = m.group(1)
    if any(k in attr.lower() for k in ['task', 'store', 'cache', 'queue', 'pool', 'list']):
        start = max(0, m.start() - 60)
        end = min(len(content), m.end() + 80)
        snippet = content[start:end].replace(chr(10), ' ')[:200]
        print(f'  {attr}: {snippet}')

print()
print('=== get_all_tasks 方法 ===')
m = re.search(r'def get_all_tasks.*?(?=    def |\Z)', content, re.DOTALL)
if m:
    text = m.group(0)
    print(text[:800])

print()
print('=== publish_task 调用（容器中心客户端）===')
m = re.search(r'self\._center_client\.publish_task\([^)]+\)', content)
if m:
    print(m.group(0))

print()
print('=== 关键：到底存到哪里？ ===')
# 查找 publish_task 后做了什么
idx = content.find('_center_client.publish_task')
if idx > 0:
    # 看后续 500 字符
    print(content[idx:idx+800])