#!/usr/bin/env python3
"""检查 config_center.py: 语法 + schema 容器连接字段"""
import ast
import sys

with open('config_center.py', 'r', encoding='utf-8') as f:
    source = f.read()

try:
    ast.parse(source)
    print('SYNTAX: OK')
except SyntaxError as e:
    print(f'SYNTAX ERROR: {e}')
    sys.exit(1)

from flask import Flask
from config_center import config_center_bp, CONFIG_SCHEMA

app = Flask(__name__)
app.register_blueprint(config_center_bp)
print(f'ROUTES: {len(app.url_map._rules)}')

test_routes = [r.rule for r in app.url_map._rules if 'test' in r.rule]
print(f'  test routes: {test_routes}')

container = CONFIG_SCHEMA['container']
fields = [f['key'] for f in container['fields']]
has_test = 'test' in container
print(f'  container fields: {fields}')
print(f'  has test action: {has_test}')
print(f'  test action: {container.get("test", {}).get("action", "N/A")}')

assert 'CONTAINER_CENTER_URL' in fields, 'Missing URL field'
assert 'CONTAINER_CENTER_SECRET' in fields, 'Missing SECRET field'
assert has_test, 'Missing test action'
assert container['test']['action'] == 'container_center', 'Wrong test action'

print('ALL CHECKS PASSED')
