import requests

r = requests.get('http://localhost:5008/api/scan-info?code=WO-202605008', timeout=10)
print(f'status: {r.status_code}')
print(f'body: {r.text[:500]}')
