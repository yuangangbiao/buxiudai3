"""测 scan-info"""
import requests
r = requests.post('http://127.0.0.1:5008/api/login', json={'username':'测试','password':'123456'}, timeout=5)
tok = r.json().get('data', {}).get('token', '')
for code in ['ORD-20260619-0001', 'ORD-202604200002', 'WO_TEST001', 'ORD-20260416-0001']:
    r = requests.get(f'http://127.0.0.1:5008/api/scan-info?code={code}', headers={'Authorization': f'Bearer {tok}'}, timeout=5)
    d = r.json()
    msg = d.get('message', 'ok') if isinstance(d, dict) else '?'
    if 'data' in d and isinstance(d['data'], dict):
        msg = d['data'].get('order_no', msg) or msg
    print(f'{code} -> {r.status_code} {str(msg)[:80]}')
