"""[审计] 冒烟测试 - 独立脚本"""
import subprocess
import os
import re

# 冒烟 1: pytest
r = subprocess.run(
    ['python', '-m', 'pytest', '--no-cov', '-q', '-p', 'no:cacheprovider',
     'tests/L1_smoke/', 'tests/L4_scenarios/', 'tests/unit/dispatch_center/'],
    capture_output=True, text=True
)
last_line = [l for l in r.stdout.split('\n') if 'passed' in l or 'failed' in l]
print('=== 冒烟 1: pytest ===')
print(last_line[-1] if last_line else 'NO RESULT')

# 冒烟 2: active from-imports
count = 0
locations = []
for root, dirs, files in os.walk('.'):
    if '.git' in root:
        continue
    for f in files:
        if not f.endswith('.py'):
            continue
        full = os.path.join(root, f)
        try:
            with open(full, 'r', encoding='utf-8') as fp:
                for i, line in enumerate(fp, 1):
                    stripped = line.strip()
                    # 排除注释和 docstring
                    if ('from desktop_container_integration import' in line
                        and not stripped.startswith('#')
                        and 'desktop_container_integration.py' not in full
                        and not stripped.startswith('"""')
                        and not stripped.startswith("'''")
                        and not '旧:' in stripped):
                        # 看是否在 docstring 里（启发式）
                        count += 1
                        locations.append((full, i, stripped[:80]))
        except Exception:
            pass
print(f'=== 冒烟 2: active from-imports: {count} ===')
for loc in locations[:10]:
    print(f'  {loc[0]}:{loc[1]}: {loc[2]}')

# 冒烟 3: 检查 __init__.py 警告数量
r2 = subprocess.run(
    ['python', '-m', 'pytest', '--no-cov', '-p', 'no:cacheprovider',
     'tests/unit/dispatch_center/test_publisher.py', '-W', 'default'],
    capture_output=True, text=True
)
warnings = [l for l in r2.stdout.split('\n') if 'warning' in l.lower() or 'WARN' in l]
print(f'=== 冒烟 3: 警告数: {len(warnings)} ===')
for w in warnings[:5]:
    print(f'  {w.strip()[:100]}')