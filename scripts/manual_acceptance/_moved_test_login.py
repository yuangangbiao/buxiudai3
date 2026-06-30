import urllib.request
import json

url = 'http://localhost:5003/api/login'
data = json.dumps({'username': '测试'}).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json; charset=utf-8'})
try:
    with urllib.request.urlopen(req) as r:
        print(json.loads(r.read().decode('utf-8')))
except Exception as e:
    print(f'Error: {e}')
