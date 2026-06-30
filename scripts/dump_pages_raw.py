import requests, re
r = requests.get('http://localhost:5008/', timeout=5)
t = r.text

# 工序任务 page
for pid, label in [('process-tasks-page', '工序任务'), ('quality-page', '质检')]:
    print(f'\n========== {label} ({pid}) ==========')
    m = re.search(rf'<div[^>]*id=["\']{re.escape(pid)}["\'][^>]*>', t)
    if not m: continue
    s = m.start()
    e = min(len(t), s + 4500)
    body = t[s:e]
    print(body)
