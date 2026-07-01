import urllib.request, json
r = urllib.request.urlopen('http://localhost:5003/api/dispatch-center/processes/f44f2f00-5629-4d5c-9b91-77457294781e')
d = json.loads(r.read())
print('code:', d.get('code'))
steps = d.get('data', {}).get('steps', [])
print('steps count:', len(steps))
for s in steps:
    print(f"  [{s['index']}] {s['name']} role={s['role']} status={s['status']}")
