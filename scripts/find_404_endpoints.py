"""6 个 404 端点的前端功能定位: 找它们在 mobile_unified.html 哪里被调用, 实现什么功能"""
import re
from pathlib import Path

FP = Path(r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\templates\mobile_unified.html')
html = FP.read_text(encoding='utf-8')

NOT_FOUND_EPS = [
    '/api/attendance/',
    '/api/quality-records',
    '/api/records',
    '/api/users',
    '/api/material-tasks',
    '/api/orders',
    '/api/process-task/ack',
]

print('=' * 70)
for ep in NOT_FOUND_EPS:
    print(f'\n=== 端点: {ep} ===')
    idx = 0
    hits = 0
    while True:
        i = html.find(ep, idx)
        if i < 0: break
        hits += 1
        if hits > 3: break
        # 找上下文
        line_start = html.rfind('\n', 0, i) + 1
        line_end = html.find('\n', i)
        if line_end < 0: line_end = i + 200
        line = html[line_start:line_end].strip()
        print(f'  @ char {i}: {line[:200]}')
        # 找最近的函数/变量名 (往前 200 字符找 function xxx 或 var xxx)
        prev = html[max(0, i-300):i]
        func_m = re.search(r'function\s+(\w+)', prev)
        var_m = re.search(r'var\s+(\w+)\s*=', prev[-200:])
        if func_m: print(f'    ↑ 函数: {func_m.group(1)}()')
        if var_m: print(f'    ↑ 变量: {var_m.group(1)}')
        idx = i + 1
    if hits == 0:
        print('  (前端未引用)')
