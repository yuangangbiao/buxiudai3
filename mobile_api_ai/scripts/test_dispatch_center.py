# -*- coding: utf-8 -*-
"""dispatch_center 导入及基本路由测试"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 确保容器中心 URL 可连接
os.environ['CONTAINER_CENTER_URL'] = os.environ.get('CONTAINER_CENTER_URL', 'http://localhost:5002')

from app import create_app

print('=== 测试开始 ===\n', flush=True)

# 1. 创建应用
try:
    app = create_app()
    print('[1] create_app(): OK', flush=True)
except Exception as e:
    print(f'[1] create_app() 失败: {e}', flush=True)
    sys.exit(1)

# 2. 检查调度中心路由注册
dispatch_routes = [r.rule for r in app.url_map.iter_rules() if '/dispatch-center' in r.rule]
print(f'[2] dispatch_center 路由数: {len(dispatch_routes)}', flush=True)
for route in sorted(dispatch_routes):
    print(f'    {route}', flush=True)

# 3. 测试健康检查和首页
with app.test_client() as c:
    # 健康检查
    r = c.get('/health')
    data = r.get_json()
    print(f'\n[3] /health: code={data.get("code") if data else "?"}', flush=True)

    r = c.get('/')
    data = r.get_json()
    print(f'    /: code={data.get("code") if data else "?"}', flush=True)

    # 4. 测试调度中心路由（可能返回空数据，但不应报错）
    test_routes = [
        '/api/dispatch-center/status',
        '/api/dispatch-center/tasks',
        '/api/dispatch-center/stats',
        '/api/dispatch-center/devices',
        '/api/dispatch-center/operators',
    ]
    print(f'\n[4] 测试路由响应', flush=True)
    for route in test_routes:
        try:
            r = c.get(route)
            status = r.status_code
            data = r.get_json() or {}
            code = data.get('code', '?')
            msg = str(data.get('message', ''))[:60]
            print(f'    {route}: HTTP {status}, code={code}, msg={msg}', flush=True)
        except Exception as e:
            print(f'    {route}: ERROR {e}', flush=True)

    # 5. 测试模板路由
    print(f'\n[5] 测试非存储路由', flush=True)
    msg_routes = [
        '/api/dispatch-center/messages/templates',
        '/api/dispatch-center/dispatch-rules',
    ]
    for route in msg_routes:
        try:
            r = c.get(route)
            status = r.status_code
            data = r.get_json() or {}
            code = data.get('code', '?')
            print(f'    {route}: HTTP {status}, code={code}', flush=True)
        except Exception as e:
            print(f'    {route}: ERROR {e}', flush=True)

    # 6. 验证内容类型
    print(f'\n[6] 验证 Content-Type', flush=True)
    for route in test_routes[:3]:
        r = c.get(route)
        ct = r.content_type or ''
        has_json = 'application/json' in ct
        print(f'    {route}: {ct} {"[OK]" if has_json else "[WARN]"}', flush=True)

print('\n=== 测试完成 ===', flush=True)
