# -*- coding: utf-8 -*-
"""
批量给 server.py 加 @require_auth + @verify_csrf_token
小钰 2026-06-23 P0 鉴权修复
"""
import sys

TARGETS = [
    # (route_path, function_name)
    ('/api/orders/upload-attachment', 'api_orders_upload_attachment'),
    ('/api/operators/import', 'api_operator_import'),
]

def main():
    path = 'desktop_web/server.py'
    with open(path, 'r', encoding='utf-8') as f:
        src = f.read()

    n = 0
    for route, func in TARGETS:
        old = f"@app.route('{route}', methods=['POST'])\ndef {func}():"
        new = f"@app.route('{route}', methods=['POST'])\n@require_auth\n@verify_csrf_token\ndef {func}():"
        if old in src:
            src = src.replace(old, new, 1)
            print(f'  [OK] {route} ({func})')
            n += 1
        else:
            print(f'  [FAIL] {route} (未找到匹配行)')

    with open(path, 'w', encoding='utf-8') as f:
        f.write(src)
    print(f'共修改 {n}/{len(TARGETS)} 个路由')

if __name__ == '__main__':
    main()
