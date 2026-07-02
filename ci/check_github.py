# -*- coding: utf-8 -*-
"""[CI Debug v3] 看具体 step 失败原因"""
import urllib.request, json
url = 'https://api.github.com/repos/yuangangbiao/buxiudai3/actions/runs?per_page=1'
req = urllib.request.Request(url, headers={'User-Agent': 'curl/7.0'})
runs = json.loads(urllib.request.urlopen(req).read())
latest = runs['workflow_runs'][0]
print(f"Latest: #{latest['run_number']} status={latest['status']} conclusion={latest['conclusion']}")
url = f"https://api.github.com/repos/yuangangbiao/buxiudai3/actions/runs/{latest['id']}/jobs"
req = urllib.request.Request(url, headers={'User-Agent': 'curl/7.0'})
data = json.loads(urllib.request.urlopen(req).read())
for j in data['jobs']:
    if j['conclusion'] == 'failure' and j['name'].startswith('2. CP-1'):
        # 看完整 step 流程
        for s in j['steps']:
            if s['conclusion'] in ('failure', 'skipped'):
                print(f"  FAILED: {s['name']} (step {s['number']})")
                print(f"    started: {s['started_at']}")
                print(f"    completed: {s['completed_at']}")
        # 整个 run 的结论
        print(f"job conclusion: {j['conclusion']}")
        print(f"job completed_at: {j['completed_at']}")
        break
