import requests
r = requests.get('http://localhost:5008/', timeout=5)
t = r.text

# 直接 dump 4 个 page 的 HTML
for page_id in ['page-scan', 'page-quality', 'page-material', 'page-outsource', 'page-process']:
    needle = f'id="{page_id}"'
    i = t.find(needle)
    if i < 0:
        needle = f"id='{page_id}'"
        i = t.find(needle)
    if i < 0:
        print(f'=== {page_id}: NOT FOUND ===')
        print()
        continue
    # 找结束 </page 标签
    end = t.find('</div>\n', i)
    if end < 0:
        end = i + 3000
    end = min(end, i + 3000)
    snippet = t[i:end]
    # 抽出 text 节点/button/input/textarea 标签
    import re
    tags = re.findall(r'<(button|h1|h2|h3|input|select|textarea|label)[^>]*>([^<]*)<', snippet)
    print(f'=== {page_id} ===')
    for tag, text in tags[:30]:
        text = text.strip()
        if text:
            print(f'  <{tag}> {text[:80]}')
    # 找 onclick="loadXxx"
    onclicks = re.findall(r'onclick=[\'"]([^\'"]+)[\'"]', snippet)
    for o in onclicks[:10]:
        print(f'  onclick: {o[:80]}')
    # 找 fetch URL
    fetches = re.findall(r"fetch\([^)]+\)", snippet)
    for f in fetches[:5]:
        print(f'  fetch: {f[:100]}')
    print()
