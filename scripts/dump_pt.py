import requests, re
r = requests.get('http://localhost:5008/', timeout=5)
t = r.text

for f in ['function selectOrderForReport', 'function showQualityDetail', 'function showDetail', 'function showReport']:
    m = re.search(re.escape(f), t)
    if not m: continue
    s = m.start()
    end_m = re.search(r'\n\s*function\s+\w+', t[s+30:])
    e = s + 30 + end_m.start() if end_m else s + 3000
    e = min(e, s + 2500)
    print(f'\n=== {f} ===')
    print(t[s:e])
