import urllib.request, json, sys
url = 'http://localhost:5003/api/dispatch-center/processes/f44f2f00-5629-4d5c-9b91-77457294781e'
try:
    resp = urllib.request.urlopen(url)
    d = json.loads(resp.read())
    print('code:', d.get('code'))
    print(json.dumps(d, indent=2, ensure_ascii=False)[:2000])
except Exception as e:
    print(f'Error: {e}')
    if hasattr(e, 'read'):
        print('Body:', e.read().decode('utf-8')[:2000])
