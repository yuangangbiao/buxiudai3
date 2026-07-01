# -*- coding: utf-8 -*-
import requests, json

BASE = 'http://127.0.0.1:5009'
urls = [
    '/face/models/blazeface.bin',
    '/models/blazeface.bin',
    '/face/models/facemesh.bin',
    '/models/facemesh.bin',
    '/face/wasm/tfjs-backend-wasm.wasm',
]
for u in urls:
    r = requests.get(BASE + u)
    ct = r.headers.get('Content-Type', 'missing')
    print(f'{u:50s} -> {r.status_code:3d}  {len(r.content):>8d} bytes  Content-Type: {ct}')
