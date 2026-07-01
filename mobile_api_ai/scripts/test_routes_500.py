import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ['CC_DATA_DIR'] = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')

from flask import Flask
from container_center.api.app import create_app
from container_center.api.configs import _store

print(f'Initial configs._store: {_store}')

app = create_app()

# Test health endpoint
print('\n=== Basic Test ===')
with app.test_client() as c:
    print('GET /api/v4/health')
    resp = c.get('/api/v4/health')
    print(f'  Status: {resp.status_code}')
    print(f'  Body: {resp.get_data(as_text=True)[:200]}')

# Check the configs module's _store
from container_center.api import configs
print(f'\nAfter create_app: configs._store = {configs._store}')

# List apps routes matching /api/v4
print(f'\n=== Flask URL Map ===')
for rule in app.url_map.iter_rules():
    if '/api/v4' in rule.rule:
        print(f'  {rule.rule} -> {rule.endpoint}')
