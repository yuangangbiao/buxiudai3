import requests, re
r = requests.get('http://localhost:5008/', timeout=5)
t = r.text

# 找 4 个核心函数的完整实现
funcs = [
    'async function loadProcessTasks',
    'async function loadQualityRecords',
    'async function loadMaterialTasks',
    'function loadOutsource',  # 各种 loadOutsource
]

for f in funcs:
    print(f'\n=== {f} ===')
    for m in re.finditer(re.escape(f), t):
        s = m.start()
        # 找函数体 (2000 字符)
        snippet = t[s:s+2000]
        # 找最近的 }  (大概)
        # 直接 dump
        print(snippet[:1800])
        print('---')
        break
