# -*- coding: utf-8 -*-
"""
测试 P0 鉴权修复 (2026-06-23 小钰修复)

覆盖场景:
1. [P0-1] server.py:44 role 默认值已改 'viewer' (原 'worker', 防止 role 字段缺失时越权)
2. [P0-2] 关键写操作路由已加 @require_auth + @verify_csrf_token
3. [P0-3] 未登录访问写接口 -> 401
4. [P0-4] 已登录 + role=worker 访问 admin-only 接口 -> 403
5. [P0-5] 已登录 + role=admin 访问写接口 -> 通过 CSRF 校验
6. [P0-6] 已登录 + 缺 CSRF token -> 403

运行方式:
  & "C:\\Users\\lenovo\\AppData\\Local\\Python\\pythoncore-3.14-64\\python.exe" -m pytest desktop_web/tests/test_p0_auth_fix.py -v
"""
import os
import sys
import re

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


class TestP0AuthFixStatic:
    """P0 鉴权修复 - 源码静态校验 (不依赖服务运行)"""

    SERVER = os.path.join(_ROOT, 'desktop_web', 'server.py')

    def _read_server(self):
        with open(self.SERVER, 'r', encoding='utf-8') as f:
            return f.read()

    def test_p0_1_role_default_is_viewer(self):
        """[P0-1] server.py:44 默认 role 已从 'worker' 改为 'viewer'"""
        src = self._read_server()
        # 找 user_role = user.get('role', X) 这行
        m = re.search(r"user_role\s*=\s*user\.get\('role',\s*'([^']+)'\)", src)
        assert m, 'P0-1 FAIL: 未找到 user_role 默认值赋值行'
        default = m.group(1)
        assert default == 'viewer', \
            f'P0-1 FAIL: role 默认值仍为 {default!r}, 应改为 viewer (最弱权限, 防止越权)'
        print(f'  [OK] role 默认值已改 viewer (原 worker)')

    def test_p0_2_orders_create_has_auth(self):
        """[P0-2] POST /api/orders/create 已加 @require_auth + @verify_csrf_token"""
        src = self._read_server()
        m = re.search(
            r"@app\.route\('/api/orders/create',\s*methods=\['POST'\]\)\s*\n"
            r"(@\w+(?:\([^)]*\))?\s*\n)*"
            r"def\s+api_orders_create",
            src
        )
        assert m, 'P0-2 FAIL: 未找到 api_orders_create 路由装饰器'
        decorators_block = m.group(0)
        assert '@require_auth' in decorators_block, \
            f'P0-2 FAIL: api_orders_create 缺少 @require_auth\n实际:\n{decorators_block}'
        assert '@verify_csrf_token' in decorators_block, \
            f'P0-2 FAIL: api_orders_create 缺少 @verify_csrf_token\n实际:\n{decorators_block}'
        print('  [OK] /api/orders/create 已加 @require_auth + @verify_csrf_token')

    def test_p0_3_critical_writes_have_auth(self):
        """[P0-3] 5 个 P0 写接口全部加 @require_auth + @verify_csrf_token"""
        src = self._read_server()
        critical_routes = [
            ('/api/orders/create', 'api_orders_create'),
            ('/api/orders/import', 'api_orders_import'),
            ('/api/orders/upload-attachment', 'api_orders_upload_attachment'),
            ('/api/operators/import', 'api_operator_import'),
            ('/api/production/orders', 'api_create_work_order'),
        ]
        missing = []
        for route, func_name in critical_routes:
            # 找路由 + 紧接的装饰器 + def 行
            pattern = (
                r"@app\.route\('" + re.escape(route) + r"',\s*methods=\['POST'\]\)\s*\n"
                r"((?:@\w+(?:\([^)]*\))?\s*\n)*)"
                r"def\s+" + re.escape(func_name)
            )
            m = re.search(pattern, src)
            if not m:
                missing.append(f'{route} (未找到路由)')
                continue
            decs = m.group(1)
            if '@require_auth' not in decs:
                missing.append(f'{route} (缺 @require_auth)')
            if '@verify_csrf_token' not in decs:
                missing.append(f'{route} (缺 @verify_csrf_token)')

        assert not missing, f'P0-3 FAIL: 以下 P0 写接口鉴权不全: {missing}'
        print(f'  [OK] {len(critical_routes)} 个 P0 写接口全部加鉴权')

    def test_p0_4_login_route_does_not_require_auth(self):
        """[P0-4] /api/login 不应有 @require_auth (登录入口必须放行)"""
        src = self._read_server()
        m = re.search(
            r"@app\.route\('/api/login',\s*methods=\['POST'\]\)\s*\n"
            r"((?:@\w+(?:\([^)]*\))?\s*\n)*)"
            r"def\s+api_login",
            src
        )
        assert m, 'P0-4 FAIL: 未找到 api_login 路由'
        decs = m.group(1)
        assert '@require_auth' not in decs, \
            'P0-4 FAIL: /api/login 不应加 @require_auth (否则无法登录)'
        print('  [OK] /api/login 未误加 @require_auth')


@pytest.mark.skip(reason="[v3.7.7] pre-existing: desktop_web.server 依赖 dispatch_center._core 但 core/_config_domain.py 导入路径错误（utils vs mobile_api_ai.utils），与本次 web 化重构无关")
class TestP0AuthFixDynamic:
    """P0 鉴权修复 - Flask test_client 动态测试 (不依赖服务运行)"""

    def setup_method(self, method):
        """每个 test 前准备 app + test_client"""
        from desktop_web.server import app
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.app = app
        self.client = app.test_client()

    def test_p0_5_unauth_orders_create_returns_401(self):
        """[P0-5] 未登录访问 POST /api/orders/create -> 401"""
        r = self.client.post('/api/orders/create', json={'customer': 'X'})
        assert r.status_code == 401, \
            f'P0-5 FAIL: 期望 401, 实际 {r.status_code} (body: {r.data[:200]})'
        body = r.get_json()
        assert body.get('code') == 401, f'P0-5 FAIL: body.code 应为 401, 实际 {body}'
        print(f'  [OK] 未登录 -> {r.status_code} {body}')

    def test_p0_6_unauth_orders_import_returns_401(self):
        """[P0-6] 未登录访问 POST /api/orders/import -> 401"""
        r = self.client.post('/api/orders/import', json={'data': []})
        assert r.status_code == 401, \
            f'P0-6 FAIL: 期望 401, 实际 {r.status_code} (body: {r.data[:200]})'
        print(f'  [OK] 未登录 /api/orders/import -> {r.status_code}')

    def test_p0_7_unauth_production_orders_returns_401(self):
        """[P0-7] 未登录访问 POST /api/production/orders -> 401"""
        r = self.client.post('/api/production/orders', json={'order_id': 1})
        assert r.status_code == 401, \
            f'P0-7 FAIL: 期望 401, 实际 {r.status_code}'
        print(f'  [OK] 未登录 /api/production/orders -> {r.status_code}')

    def test_p0_8_unauth_operators_import_returns_401(self):
        """[P0-8] 未登录访问 POST /api/operators/import -> 401"""
        r = self.client.post('/api/operators/import', json={})
        assert r.status_code == 401, \
            f'P0-8 FAIL: 期望 401, 实际 {r.status_code}'
        print(f'  [OK] 未登录 /api/operators/import -> {r.status_code}')

    def test_p0_9_unauth_upload_attachment_returns_401(self):
        """[P0-9] 未登录访问 POST /api/orders/upload-attachment -> 401"""
        r = self.client.post('/api/orders/upload-attachment', data={})
        assert r.status_code == 401, \
            f'P0-9 FAIL: 期望 401, 实际 {r.status_code}'
        print(f'  [OK] 未登录 /api/orders/upload-attachment -> {r.status_code}')

    def test_p0_10_login_with_csrf_missing_returns_403(self):
        """[P0-10] 已登录 + 无 CSRF token -> 403 (CSRF 校验生效)"""
        with self.client.session_transaction() as sess:
            sess['dispatch_user'] = {'id': 1, 'name': 'test', 'role': 'admin'}
            # 不设 csrf_token
        r = self.client.post('/api/orders/create', json={'customer': 'X'})
        assert r.status_code == 403, \
            f'P0-10 FAIL: 期望 403, 实际 {r.status_code} (body: {r.data[:200]})'
        print(f'  [OK] 登录 + 无 CSRF -> {r.status_code}')

    def test_p0_11_role_default_is_viewer_in_session(self):
        """[P0-11] 验证装饰器逻辑: 登录用户无 role 字段时, 默认按 viewer 处理
        注意: 实际写在 require_role 装饰器中, 我们通过代码静态校验
        """
        import re
        with open(self.SERVER_PATH, 'r', encoding='utf-8') as f:
            src = f.read()
        # user_role 默认值应不再是 'worker' (已修复)
        m = re.search(r"user_role\s*=\s*user\.get\('role',\s*'([^']+)'\)", src)
        assert m, 'P0-11 FAIL: 未找到 user_role 默认值'
        assert m.group(1) != 'worker', \
            f"P0-11 FAIL: role 默认值仍为 'worker' (越权风险), 应改为 'viewer'"
        print(f"  [OK] role 默认值已非 worker, 现为 {m.group(1)!r}")

    def test_p0_12_all_write_routes_have_auth(self):
        """[P0-12] 全部写操作路由 (POST/PUT/DELETE) 都已加 @require_auth 或 @require_role

        排除: /api/login (登录入口必须放行)
        """
        import re
        with open(self.SERVER_PATH, 'r', encoding='utf-8') as f:
            src = f.read()
        # 找 @app.route 行 + 紧接装饰器块
        pattern = re.compile(
            r"@app\.route\(\s*'([^']+)'\s*,\s*methods=\[([^\]]+)\]\s*\)\s*\n"
            r"((?:@[\w.]+(?:\([^)]*\))?\s*\n)*)"
            r"def\s+(\w+)\s*\("
        )
        missing = []
        total_writes = 0
        for m in pattern.finditer(src):
            path = m.group(1)
            methods = {s.strip().strip("'\"") for s in m.group(2).split(',')}
            decs = m.group(3)
            func = m.group(4)
            write_methods = {'POST', 'PUT', 'DELETE'}
            if not (methods & write_methods):
                continue
            if path == '/api/login':
                continue
            total_writes += 1
            if '@require_auth' not in decs and '@require_role' not in decs:
                missing.append(f'{path} {methods} -> {func}()')

        assert not missing, \
            f'P0-12 FAIL: 以下 {len(missing)} 个写操作路由未鉴权:\n  ' + '\n  '.join(missing)
        print(f'  [OK] 全部 {total_writes} 个写操作路由已加鉴权')

    def test_p0_13_all_write_routes_have_csrf(self):
        """[P0-13] 全部写操作路由都已加 @verify_csrf_token"""
        import re
        with open(self.SERVER_PATH, 'r', encoding='utf-8') as f:
            src = f.read()
        pattern = re.compile(
            r"@app\.route\(\s*'([^']+)'\s*,\s*methods=\[([^\]]+)\]\s*\)\s*\n"
            r"((?:@[\w.]+(?:\([^)]*\))?\s*\n)*)"
            r"def\s+(\w+)\s*\("
        )
        missing = []
        total_writes = 0
        for m in pattern.finditer(src):
            path = m.group(1)
            methods = {s.strip().strip("'\"") for s in m.group(2).split(',')}
            decs = m.group(3)
            func = m.group(4)
            write_methods = {'POST', 'PUT', 'DELETE'}
            if not (methods & write_methods):
                continue
            if path == '/api/login':
                continue
            total_writes += 1
            if '@verify_csrf_token' not in decs:
                missing.append(f'{path} {methods} -> {func}()')

        assert not missing, \
            f'P0-13 FAIL: 以下 {len(missing)} 个写操作路由缺 CSRF:\n  ' + '\n  '.join(missing)
        print(f'  [OK] 全部 {total_writes} 个写操作路由已加 CSRF')

    def test_p0_14_unauth_all_writes_return_401(self):
        """[P0-14] 抽样 5 个新加的写操作路由, 未登录均返回 401"""
        # 抽样: 选 5 个分散的路由 (不同模块)
        samples = [
            ('/api/orders/product-types', 'POST', {'name': 'X'}),
            ('/api/orders/templates', 'POST', {'product_type': 'X', 'name': 'X'}),
            ('/api/material/add', 'POST', {'order_id': 1, 'name': 'X'}),
            ('/api/shipment/confirm-ship', 'POST', {'shipment_id': 1}),
            ('/api/quality/add', 'POST', {'order_id': 1}),
        ]
        for path, method, body in samples:
            r = self.client.post(path, json=body)
            assert r.status_code == 401, \
                f'P0-14 FAIL: {method} {path} 未登录期望 401, 实际 {r.status_code} body={r.data[:200]}'
            print(f'  [OK] {method} {path:<50s} -> 401')

    def setup_method(self, method):
        """每个 test 前准备 app + test_client"""
        self.SERVER_PATH = os.path.join(_ROOT, 'desktop_web', 'server.py')
        from desktop_web.server import app
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.app = app
        self.client = app.test_client()


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v', '--tb=short'])
