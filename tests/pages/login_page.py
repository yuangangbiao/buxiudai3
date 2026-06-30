# -*- coding: utf-8 -*-
"""
桌面端登录页 - Page Object
"""
import logging
from tests.pages.base_page import BasePage

logger = logging.getLogger(__name__)


class LoginPage(BasePage):
    """5001 桌面端登录页"""

    # 选择器集中管理（修改 UI 时只需改这里）
    SELECTORS = {
        'username': 'input[name="username"], #u',
        'password': 'input[name="password"], #p',
        'submit': 'button[type="submit"], #b',
        'error_msg': '.error, .alert-danger, [class*="error"]',
    }

    SUCCESS_URL_PATTERN = '/orders'

    def login(self, username: str, password: str):
        """执行登录"""
        self.goto('/login')
        self.fill(self.SELECTORS['username'], username)
        self.fill(self.SELECTORS['password'], password)
        self.click(self.SELECTORS['submit'])
        self.wait_for_url(self.SUCCESS_URL_PATTERN, timeout=10000)
        logger.info(f"✅ 登录成功: {username}")
        return self

    def get_error(self) -> str:
        """获取错误信息"""
        if self.is_visible(self.SELECTORS['error_msg']):
            return self.text(self.SELECTORS['error_msg'])
        return ''

    def login_as_role(self, role: str):
        """根据角色登录（使用 fixture 中的用户）"""
        from tests.fixtures.users import get_user
        user = get_user(role)
        return self.login(user['name'], user['password'])
