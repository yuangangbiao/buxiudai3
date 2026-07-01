import urllib.request, json

# 1. 查待入库列表
resp = urllib.request.urlopen('http://127.0.0.1:5003/api/dispatch-center/pending-warehousing', timeout=5)
data = json.loads(resp.read())
print("=== 待入库工单 ===")
print(json.dumps(data, indent=2, ensure_ascii=False))

# 2. 查所有流程状态
resp2 = urllib.request.urlopen('http://127.0.0.1:5003/api/dispatch-center/processes', timeout=5)
procs_data = json.loads(resp2.read())
procs = procs_data.get('data', {}).get('processes', []) or procs_data.get('data', []) or []
print(f"\n=== 所有流程 (共{len(procs)}个) ===")
for p in procs:
    wid = p.get('order_no', '')
    print(f"  工单={wid}  状态={p.get('status','')}  step={p.get('current_step',0)}  awaiting={p.get('awaiting_confirmation')}  step_status={p.get('awaiting_step_status','')}")

# 3. 测试代理
resp3 = urllib.request.urlopen('http://127.0.0.1:5008/api/warehousing/pending', timeout=5)
proxy_data = json.loads(resp3.read())
print(f"\n=== 通过代理(5008)查询 ===")
print(json.dumps(proxy_data, indent=2, ensure_ascii=False))
