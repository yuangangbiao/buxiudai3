"""探测测试账号"""
import requests

for name, pwd in [
    ('admin', 'admin123'),
    ('worker01', '123456'),
    ('qc01', '123456'),
    ('viewer1', '123456'),
]:
    r = requests.post('http://127.0.0.1:5001/api/login',
                      json={'username': name, 'password': pwd}, timeout=5)
    data = r.json()
    print(f'{name:12s}/{pwd:10s}: HTTP={r.status_code} code={data.get("code")} msg={data.get("message","")[:50]}')
