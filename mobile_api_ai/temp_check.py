import urllib.request, json

api = urllib.request.urlopen('http://localhost:5008/api/scan-info?code=ORD-202604290001&_t=' + str(hash('now')))
info = json.loads(api.read().decode('utf-8'))
data = info.get('data', {})
print('=== 报工系统 API (端口5008) ===')
print(f'总数量={data.get("quantity")} 总完成量={data.get("total_completed_qty")}')
for p in data.get('processes', []):
    print(f'  {p[\"step_name\"]:<20} {p[\"completed_qty\"]}/{p[\"required_qty\"]}')
