# -*- coding: utf-8 -*-
"""
移动端登录页 - Page Object
"""
import logging
from tests.pages.base_page import BasePage

logger = logging.getLogger(__name__)


class MobileLoginPage(BasePage):
    """5008 移动端登录页"""

    SELECTORS = {
        'username': 'input[name="username"], #u',
        'password': 'input[name="password"], #p',
        'submit': 'button[type="submit"], #b',
    }

    SUCCESS_URL_PATTERN = '/tasks'

    def login(self, username: str, password: str):
        self.goto('/login')
        self.fill(self.SELECTORS['username'], username)
        self.fill(self.SELECTORS['password'], password)
        self.click(self.SELECTORS['submit'])
        self.wait_for_url(self.SUCCESS_URL_PATTERN, timeout=10000)
        return self

    def login_as_role(self, role: str):
        from tests.fixtures.users import get_user
        user = get_user(role)
        return self.login(user['name'], user['password'])
