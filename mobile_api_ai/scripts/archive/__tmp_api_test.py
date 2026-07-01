import requests, json

# 验证流程列表
r = requests.get('http://localhost:5003/api/dispatch-center/processes', timeout=5)
d = r.json()
print(f'processes: code={d["code"]}, count={len(d.get("data",[]))}')

# 验证工单详情
r2 = requests.get('http://localhost:5003/api/dispatch-center/workorder/WO-202605009', timeout=5)
d2 = r2.json()
print(f'workorder_detail: code={d2["code"]}')
if d2.get('data'):
    print(f'  status={d2["data"].get("status")}, product={d2["data"].get("product_name")}')
