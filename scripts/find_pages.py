import requests, re
r = requests.get('http://localhost:5008/', timeout=5)
t = r.text

# 找 4 个分页面的功能/特征
for kw in ['scan-page', 'quality-page', 'material-page', 'outsource-page']:
    print(f'=== {kw} ===')
    matches = [m.start() for m in re.finditer(re.escape(kw), t)]
    print(f'  hits: {len(matches)} @ {matches[:3]}')
    if matches:
        i = matches[0]
        # 往前找 showPage 调用
        s = max(0, t.rfind('showPage(', 0, i))
        end = t.find('\nfunction', i) if t.find('\nfunction', i) > 0 else t.find('function showScanReport', i)
        if end < 0: end = min(len(t), i + 1500)
        print(f'  showPage @ {s}, end @ {end}')
        snippet = t[s:min(end, s+1500)]
        snippet = snippet.replace('\n', ' ')
        print(f'  {snippet[:1200]}')
    print()
