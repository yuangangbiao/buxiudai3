import requests, json

tests = [
    ('channel=app', {'content': 'app test', 'msg_type': 'text', 'channel': 'app'}),
    ('channel=webhook', {'content': 'webhook test', 'msg_type': 'text', 'channel': 'webhook'}),
    ('channel=all', {'content': 'all test', 'msg_type': 'text', 'channel': 'all'}),
    ('default', {'content': 'default test', 'msg_type': 'text'}),
]

for label, body in tests:
    r = requests.post('http://127.0.0.1:5002/api/v4/messages', json=body, timeout=15)
    print(f'=== {label} ===')
    print(json.dumps(r.json(), ensure_ascii=False, indent=2))
    print()