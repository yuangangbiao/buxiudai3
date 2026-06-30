# -*- coding: utf-8 -*-
"""
统一登录辅助 - 支持 5001/5003/5008 三个服务

修复 P0-3: 提供 conftest.py:130 所需的 login_as 真实实现
"""
import logging
from typing import Optional

from playwright.sync_api import Page, Browser

from tests.core._config import SERVICES
from tests.fixtures.users import get_user_for_service

logger = logging.getLogger(__name__)


# ==================== 登录 URL 与表单字段映射 ====================
LOGIN_CONFIG = {
    'desktop_web': {
        'url': '/login',
        'name_field': 'input[name="username"], #u',
        'pwd_field': 'input[name="password"], #p',
        'submit': 'button[type="submit"], #b',
        'success_url_contains': '/orders',
    },
    'mobile': {
        'url': '/login',
        'name_field': 'input[name="username"], #u',
        'pwd_field': 'input[name="password"], #p',
        'submit': 'button[type="submit"], #b',
        'success_url_contains': '/tasks',
    },
    'dispatch': {
        'url': '/api/dispatch-center/login',
        # dispatch 走 API 而非 UI
        'api_login': True,
    },
    'container': {
        'url': '/api/container/login',
        'api_login': True,
    },
}


def login_as(page: Page, service: str, role: str = 'admin') -> dict:
    """
    在指定页面以指定角色登录指定服务

    Args:
        page: Playwright Page 对象
        service: 服务名（desktop_web/mobile/dispatch/container）
        role: 角色名（admin/manager/operator/qc/warehouse）

    Returns:
        user dict
    """
    user = get_user_for_service(service, role)
    config = LOGIN_CONFIG.get(service)

    if not config:
        raise ValueError(f"未配置服务: {service}, 可选: {list(LOGIN_CONFIG.keys())}")

    base_url = SERVICES[service]

    if config.get('api_login'):
        # API 登录
        _api_login(page, base_url, config, user)
    else:
        # UI 登录
        _ui_login(page, base_url, config, user)

    logger.info(f"✅ {service} 登录成功: {user['name']} ({user['role']})")
    return user


def _ui_login(page: Page, base_url: str, config: dict, user: dict):
    """UI 表单登录"""
    page.goto(f"{base_url}{config['url']}", wait_until='domcontentloaded')
    page.fill(config['name_field'], user['name'])
    page.fill(config['pwd_field'], user['password'])
    page.click(config['submit'])
    # 等待跳转
    success_marker = config.get('success_url_contains')
    if success_marker:
        page.wait_for_url(f"**{success_marker}**", timeout=10000)


def _api_login(page: Page, base_url: str, config: dict, user: dict):
    """API 登录 - 通过 page context 的 request"""
    response = page.request.post(
        f"{base_url}{config['url']}",
        data={
            'username': user['name'],
            'password': user['password'],
        },
    )
    if response.status >= 400:
        raise RuntimeError(f"API 登录失败: {response.status} {response.text()}")


def login_all_services(page: Page, role: str = 'admin') -> dict:
    """登录所有支持 UI 的服务"""
    results = {}
    for service in ['desktop_web', 'mobile']:
        try:
            results[service] = login_as(page, service, role)
        except Exception as e:
            logger.warning(f"⚠️ {service} 登录失败: {e}")
    return results


def logout(page: Page, service: str = 'desktop_web'):
    """登出"""
    base_url = SERVICES[service]
    config = LOGIN_CONFIG.get(service, {})
    logout_url = config.get('logout_url', '/logout')

    try:
        page.goto(f"{base_url}{logout_url}", timeout=5000)
    except Exception as e:
        logger.debug(f"登出失败（忽略）: {e}")


__all__ = ['login_as', 'login_all_services', 'logout', 'LOGIN_CONFIG']


# 修复 P0-3: 兼容历史导入名 LoginHelper
class LoginHelper:
    """LoginHelper 兼容类 - 内部调用 login_as 函数"""

    def __init__(self, page=None):
        self.page = page

    def login(self, page=None, service: str = 'desktop_web', role: str = 'admin') -> dict:
        page = page or self.page
        return login_as(page, service, role)

    def logout(self, page=None, service: str = 'desktop_web'):
        page = page or self.page
        logout(page, service)
