# -*- coding: utf-8 -*-
"""
Page Object 模式 - 修复 A7

所有 UI 选择器和业务操作封装到 Page 类中。
测试通过 Page Object 调用，避免硬编码 selector 和重复操作。
"""
from .base_page import BasePage
from .login_page import LoginPage
from .orders_page import OrdersPage
from .process_page import ProcessPage
from .quality_page import QualityPage
from .mobile_login_page import MobileLoginPage
from .mobile_tasks_page import MobileTasksPage

__all__ = [
    'BasePage',
    'LoginPage', 'OrdersPage', 'ProcessPage', 'QualityPage',
    'MobileLoginPage', 'MobileTasksPage',
]
