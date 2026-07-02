import subprocess, os

cwd = r'd:\yuan\不锈钢网带跟单3.0'

# Verify YAML syntax
import yaml
try:
    with open(os.path.join(cwd, '.github/workflows/ci.yml'), 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f.read())
    print(f"YAML syntax: OK")
    print(f"Job name: {data['jobs']['ci']['name']}")
    print(f"Total steps: {len(data['jobs']['ci']['steps'])}")
except Exception as e:
    print(f"YAML syntax ERROR: {e}")

# Count servers
yml = open(os.path.join(cwd, '.github/workflows/ci.yml'), 'r', encoding='utf-8').read()
servers = ['5001', '5002', '5003', '5008', '8008']
for s in servers:
    count = yml.count(f' - name: Start {s}')
    print(f"Server {s}: {count} start step(s)")
