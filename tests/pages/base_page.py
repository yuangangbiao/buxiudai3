# -*- coding: utf-8 -*-
"""
Page Object 基类

所有具体页面继承此类，复用通用方法。
"""
import logging
from typing import Optional
from playwright.sync_api import Page, Locator

from tests.core._config import SCREENSHOTS_DIR, SERVICES
from tests.core.retry import smart_retry

logger = logging.getLogger(__name__)


class BasePage:
    """所有 Page Object 的基类"""

    def __init__(self, page: Page, service: str = 'desktop_web'):
        """
        Args:
            page: Playwright Page 对象
            service: 服务名（desktop_web/mobile/dispatch）
        """
        self.page = page
        self.service = service
        self.base_url = SERVICES.get(service, SERVICES['desktop_web'])

    # ==================== 通用操作 ====================

    def goto(self, path: str, wait_until: str = 'domcontentloaded', timeout: int = 30000):
        """导航到指定路径"""
        url = f"{self.base_url}{path}" if path.startswith('/') else path
        logger.debug(f"导航: {url}")
        self.page.goto(url, wait_until=wait_until, timeout=timeout)
        return self

    def wait_for_url(self, pattern: str, timeout: int = 10000):
        """等待 URL 匹配"""
        self.page.wait_for_url(f"**{pattern}**", timeout=timeout)
        return self

    def find(self, selector: str, **kwargs) -> Locator:
        """查找元素"""
        return self.page.locator(selector, **kwargs)

    def fill(self, selector: str, value: str):
        """填写表单"""
        self.page.fill(selector, value)
        return self

    def click(self, selector: str, **kwargs):
        """点击"""
        self.page.click(selector, **kwargs)
        return self

    def text(self, selector: str) -> str:
        """获取文本"""
        return self.page.text_content(selector) or ''

    def is_visible(self, selector: str, timeout: int = 5000) -> bool:
        """检查元素是否可见"""
        try:
            return self.page.locator(selector).first.is_visible(timeout=timeout)
        except Exception:
            return False

    def wait_for(self, selector: str, timeout: int = 10000):
        """等待元素出现"""
        self.page.wait_for_selector(selector, timeout=timeout)
        return self

    def screenshot(self, name: str = None) -> str:
        """截图"""
        from datetime import datetime
        name = name or f"{self.__class__.__name__}_{datetime.now().strftime('%H%M%S')}.png"
        path = SCREENSHOTS_DIR / name
        self.page.screenshot(path=str(path), full_page=True)
        logger.info(f"📸 截图: {path}")
        return str(path)

    # ==================== 装饰器集成 ====================

    @staticmethod
    def with_retry(max_attempts: int = 3):
        """装饰器：重试"""
        return smart_retry(max_attempts=max_attempts, backoff='exponential')
