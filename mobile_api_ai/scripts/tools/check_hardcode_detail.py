"""检查 6 个标记项的具体位置和上下文"""
import re
from pathlib import Path

BASE = Path(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai')

issues = [
    ('dispatch_center.py', 'SCHEDULER_INTERVAL'),
    ('container_center_api.py', 'REDIS_PORT'),
    ('container_center_api.py', 'CONFIG_MAX_VERSIONS'),
    ('container_center/storage/document_store.py', '9200'),
    ('container_center/storage/config_store.py', 'CC_DATA_DIR'),
    ('container_center/storage/router.py', 'CC_DATA_DIR'),
]

for fname, pattern in issues:
    fp = BASE / fname
    if not fp.exists():
        print(f'{fname}: 文件不存在')
        continue
    text = fp.read_text('utf-8')
    lines = text.split('\n')
    print(f'--- {fname} (搜索: {pattern}) ---')
    for i, line in enumerate(lines, 1):
        if re.search(pattern, line, re.IGNORECASE):
            # 显示上下一行上下文
            start = max(0, i-2)
            end = min(len(lines), i+1)
            for j in range(start, end):
                marker = '>>>' if j+1 == i else '   '
                print(f'  {marker} L{j+1}: {lines[j].strip()[:120]}')
            print()
