import requests, re
r = requests.get('http://localhost:5008/', timeout=5)
t = r.text

# 4 个任务页 id
pages = {
    'process-tasks-page':   '工序任务',
    'quality-page':         '质检',
    'material-page':        '物料',
    'outsource-page':       '外协',
}

for pid, label in pages.items():
    print(f'=== {label} (id={pid}) ===')
    # 找 page 的 div 范围: <div id="X" class="page">
    m = re.search(rf'<div[^>]*id=["\']{re.escape(pid)}["\'][^>]*>', t)
    if not m:
        print(f'  NOT FOUND')
        print()
        continue
    start = m.end()
    # 找匹配的 </div>  (简单的 div nesting 计数)
    depth = 1
    i = start
    while i < len(t) and depth > 0:
        nxt = t.find('<div', i)
        nxt2 = t.find('</div>', i)
        if nxt2 < 0: break
        if nxt >= 0 and nxt < nxt2:
            depth += 1
            i = nxt + 4
        else:
            depth -= 1
            i = nxt2 + 6
    end = i
    body = t[start:end]

    # 抽 button 标签
    btns = re.findall(r'<button[^>]*>([^<]+)</button>', body)
    print(f'  按钮 ({len(btns)}):')
    for b in btns[:15]:
        print(f'    - {b.strip()[:60]}')

    # 抽 h2/h3 标题
    hs = re.findall(r'<h[1-3][^>]*>([^<]+)</h[1-3]>', body)
    if hs:
        print(f'  标题:')
        for h in hs[:8]:
            print(f'    - {h.strip()[:60]}')

    # 抽 input/select placeholder
    inputs = re.findall(r'<input[^>]*placeholder=["\']([^"\']+)["\']', body)
    if inputs:
        print(f'  输入框:')
        for ipt in inputs[:8]:
            print(f'    - {ipt[:50]}')

    # 抽 onclicks
    onclicks = re.findall(r'onclick=[\'"]([^\'"]+)[\'"]', body)
    if onclicks:
        print(f'  操作:')
        for o in onclicks[:8]:
            print(f'    - {o[:60]}')

    # 抽 fetch 调用
    fetches = re.findall(r"fetch\(['\"]([^'\"]+)['\"]", body)
    if fetches:
        print(f'  API 调用:')
        for f in fetches[:5]:
            print(f'    - {f}')

    # 抽 data-action / data-type 等
    das = re.findall(r'data-action=[\'"]([^\'"]+)[\'"]', body)
    if das:
        print(f'  data-action:')
        for d in das[:8]:
            print(f'    - {d}')

    print()
