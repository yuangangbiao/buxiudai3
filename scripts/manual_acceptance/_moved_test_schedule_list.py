import urllib.request, json, base64

token = base64.b64encode("15:测试".encode('utf-8')).decode('ascii')
headers = {'X-Dispatch-Token': token}
url = 'http://localhost:5001/api/process/list'
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as r:
    data = json.loads(r.read().decode('utf-8'))
print(json.dumps(data, ensure_ascii=False, indent=2)[:2000])
