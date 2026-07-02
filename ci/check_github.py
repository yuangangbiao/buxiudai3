# -*- coding: utf-8 -*-
"""[CI Debug] 看 CP-1 失败的具体 log"""
import urllib.request, json
url = 'https://api.github.com/repos/yuangangbiao/buxiudai3/actions/runs?per_page=1'
req = urllib.request.Request(url, headers={'User-Agent': 'curl/7.0'})
runs = json.loads(urllib.request.urlopen(req).read())
latest = runs['workflow_runs'][0]
print(f"Latest: #{latest['run_number']} sha={latest['head_sha'][:8]} status={latest['status']}")
url = f"https://api.github.com/repos/yuangangbiao/buxiudai3/actions/runs/{latest['id']}/jobs"
req = urllib.request.Request(url, headers={'User-Agent': 'curl/7.0'})
data = json.loads(urllib.request.urlopen(req).read())
for j in data['jobs']:
    if j['name'].startswith('2. CP-1'):
        # 看步骤细节
        for s in j['steps']:
            if s['conclusion'] == 'failure':
                print(f"FAILED step: {s['name']}")
                print(f"  number: {s['number']}")
                print(f"  started: {s['started_at']}")
                print(f"  completed: {s['completed_at']}")
        print(f"job_id: {j['id']}")
        # 这个 step 的 log 通常在 logs_url 里
        print(f"logs_url: {j['url']}")
        break
