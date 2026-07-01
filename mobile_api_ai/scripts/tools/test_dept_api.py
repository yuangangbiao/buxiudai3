import requests, json, sys, os
outfile = os.path.join(os.path.dirname(__file__), 'test_output.txt')
f = open(outfile, 'w', encoding='utf-8')

def log(msg):
    print(msg)
    f.write(msg + '\n')

log('=== 测试 force_cloud=1 ===')
r = requests.get('http://127.0.0.1:5003/api/dispatch-center/operators/wechat-departments?force_cloud=1', timeout=30)
d = r.json()
log(f'HTTP {r.status_code}, code={d.get("code")}')
dd = d.get('data', {})
log(f'source={dd.get("source","?")}')
log(f'flat_count={dd.get("flat_count")}')
depts = dd.get('departments', [])
log(f'root_depts={len(depts)}')
for dept in depts:
    log(f'  ├ {dept.get("name")} (members={len(dept.get("members",[]))})')
    for child in dept.get('children', []):
        log(f'  │ └ {child.get("name")} (members={len(child.get("members",[]))})')
        for gc in child.get('children', []):
            log(f'  │   └ {gc.get("name")} (members={len(gc.get("members",[]))})')

if d.get('code') != 0:
    log(f'ERROR: {d.get("message")}')
    log(json.dumps(d, ensure_ascii=False, indent=2)[:2000])

log('\n=== 测试 force_cloud=0（验证缓存）===')
r2 = requests.get('http://127.0.0.1:5003/api/dispatch-center/operators/wechat-departments', timeout=10)
d2 = r2.json()
dd2 = d2.get('data', {})
log(f'code={d2.get("code")}, source={dd2.get("source","?")}, flat_count={dd2.get("flat_count")}')

f.close()
print(f'\n结果已写入: {outfile}')
