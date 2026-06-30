import requests, re
r = requests.get('http://localhost:5008/', timeout=5)
t = r.text

# 找 4 个函数的 inline 实现
funcs = [
    'function loadProcessTasks',
    'function loadQualityRecords',
    'function loadMaterialTasks',
    'function loadOutsource',
    'function scanForProcessTasks',
    'function submitQualityReport',
    'function selectQualityResult',
    'function showOutsource',
    'function showMaterial',
]

for f in funcs:
    m = re.search(re.escape(f), t)
    if not m:
        print(f'\n=== {f} === NOT FOUND')
        continue
    s = m.start()
    # 找下一个 function 开始 (即函数结束位置)
    end_m = re.search(r'\n\s*function\s+\w+', t[s+30:])
    end = s + 30 + end_m.start() if end_m else s + 2000
    end = min(end, s + 2500)
    print(f'\n=== {f} ===')
    print(t[s:end])
