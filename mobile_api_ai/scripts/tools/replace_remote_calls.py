import re
import sys

fp = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\dispatch_center.py'
with open(fp, 'r', encoding='utf-8') as f:
    content = f.read()

new_func_start = content.find('def _get_cached_work_orders')
new_func_end = content.find('\ndef ', new_func_start + 1)
if new_func_end == -1:
    new_func_end = len(content)

pattern = r"_get_client\(\)\.query_documents\('work_order', page=1, size=\d+\)"
matches = list(re.finditer(pattern, content))
count = 0
for m in matches:
    start = m.start()
    if new_func_start <= start < new_func_end:
        continue
    old = m.group()
    size_match = re.search(r'size=(\d+)', old)
    if size_match:
        new = f"_get_cached_work_orders(page=1, size={size_match.group(1)})"
        content = content[:start] + new + content[m.end():]
        count += 1

with open(fp, 'w', encoding='utf-8') as f:
    f.write(content)

print(f'Replaced {count} occurrences')
