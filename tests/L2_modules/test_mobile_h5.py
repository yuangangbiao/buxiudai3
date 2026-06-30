"""L2: 移动端 H5 页面测试"""
import pytest
from playwright.sync_api import sync_playwright

from tests.conftest import SERVICES
from tests.core.login import LoginHelper
from tests.core.assertions import S


@pytest.mark.L2
@pytest.mark.mobile
class TestMobileH5:
    """移动端 H5 测试"""
    
    @pytest.fixture
    def mobile_browser(self):
        """移动端浏览器 fixture"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 375, 'height': 667},  # iPhone 8
                device_scale_factor=2,
                is_mobile=True,
                has_touch=True,
                user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15'
            )
            yield context
            context.close()
            browser.close()
    
    def test_mobile_login_page(self, mobile_browser):
        """移动端登录页"""
        page = mobile_browser.new_page()
        page.goto(f'{SERVICES["mobile"]}/login')
        page.wait_for_load_state('networkidle')
        
        # 检查关键元素
        assert page.locator('input[name=name], input[name=username]').count() > 0
        S.assert_no_error(page)
        page.close()
    
    def test_mobile_my_tasks(self, mobile_browser):
        """移动端我的任务"""
        page = mobile_browser.new_page()
        # 先登录获取 cookie
        LoginHelper.login_5008('YuanGangBiao')
        
        page.goto(f'{SERVICES["mobile"]}/my-tasks')
        page.wait_for_load_state('networkidle')
        S.assert_no_error(page)
        page.close()
    
    def test_mobile_scan_page(self, mobile_browser):
        """移动端扫码报工页"""
        page = mobile_browser.new_page()
        LoginHelper.login_5008('YuanGangBiao')
        
        page.goto(f'{SERVICES["mobile"]}/scan')
        page.wait_for_load_state('networkidle')
        S.assert_no_error(page)
        page.close()
    
    def test_mobile_attendance(self, mobile_browser):
        """移动端考勤"""
        page = mobile_browser.new_page()
        LoginHelper.login_5008('YuanGangBiao')
        
        page.goto(f'{SERVICES["mobile"]}/attendance')
        page.wait_for_load_state('networkidle')
        S.assert_no_error(page)
        page.close()


@pytest.mark.L2
@pytest.mark.mobile
class TestMobileResponsive:
    """移动端响应式"""
    
    @pytest.mark.parametrize('viewport', [
        {'width': 375, 'height': 667, 'name': 'iPhone-8'},
        {'width': 414, 'height': 896, 'name': 'iPhone-XR'},
        {'width': 768, 'height': 1024, 'name': 'iPad'},
    ])
    def test_mobile_responsive(self, viewport):
        """响应式布局测试"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': viewport['width'], 'height': viewport['height']},
                is_mobile=viewport['width'] < 768,
            )
            page = context.new_page()
            page.goto(f'{SERVICES["mobile"]}/login')
            page.wait_for_load_state('networkidle')
            
            # 截图保存
            page.screenshot(path=f'tests/reports/screenshots/mobile_{viewport["name"]}.png')
            
            # 验证元素可见
            assert page.locator('input').first.is_visible()
            
            context.close()
            browser.close()
