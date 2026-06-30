# -*- coding: utf-8 -*-
"""验证 server.py 路由表是否正确加载"""
import sys
import os
import io

# Windows console UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, r'd:\yuan\不锈钢网带跟单3.0\desktop_web')

try:
    import server
    rules = list(server.app.url_map.iter_rules())
    api_routes = [r for r in rules if 'api' in str(r)]
    print(f'TOTAL_ROUTES={len(rules)}')
    print(f'API_ROUTES={len(api_routes)}')
    print(f'HEALTH={any("/api/health" in str(r) for r in rules)}')
    print(f'QUALITY_LIST={any(str(r) == "/api/quality/list" for r in rules)}')
    print(f'QUALITY_ADMIN_LIST={any(str(r) == "/api/quality/admin-list" for r in rules)}')
    # 关键路由
    for path in ['/api/health', '/api/quality/list', '/api/quality/admin-list',
                 '/api/process/list', '/api/process/admin-list',
                 '/api/orders', '/api/shipment/company/list', '/api/material/list']:
        match = [r for r in rules if str(r) == path]
        print(f'  {path}: {"FOUND" if match else "MISSING"}')
except Exception as e:
    import traceback
    print(f'IMPORT_FAILED: {e}')
    traceback.print_exc()
