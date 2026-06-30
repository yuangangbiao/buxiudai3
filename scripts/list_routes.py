import urllib.request, json, base64

token = base64.b64encode("15:测试".encode('utf-8')).decode('ascii')
headers = {'X-Dispatch-Token': token}
url = 'http://localhost:5001/api/process/list'
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as r:
    data = json.loads(r.read().decode('utf-8'))
print(json.dumps(data, ensure_ascii=False, indent=2)[:3000])

print()
print('=== production/list ===')
req2 = urllib.request.Request('http://localhost:5001/api/production/list', headers=headers)
with urllib.request.urlopen(req2) as r2:
    data2 = json.loads(r2.read().decode('utf-8'))
print(json.dumps(data2, ensure_ascii=False, indent=2)[:1500])
