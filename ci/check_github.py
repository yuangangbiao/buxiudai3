# -*- coding: utf-8 -*-
import urllib.request, json
url = 'https://api.github.com/repos/yuangangbiao/buxiudai3/actions/runs/28567046686/jobs'
req = urllib.request.Request(url, headers={'User-Agent': 'curl/7.0'})
data = json.loads(urllib.request.urlopen(req).read())
for j in data['jobs']:
    name = j['name']
    status = j['conclusion']
    print(f'{status:8} | {name}')
