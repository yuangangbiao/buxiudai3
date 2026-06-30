import requests
fake_token = 'a' * 64
r = requests.get(
    'http://127.0.0.1:5003/api/dispatch-center/order-status-list',
    cookies={'dispatch_token': fake_token},
    timeout=5,
)
print(f'5003 order-status-list: {r.status_code} | {r.text[:100]}')
r2 = requests.get('http://127.0.0.1:5003/', timeout=5)
print(f'5003 root: {r2.status_code} | {r2.text[:100]}')
