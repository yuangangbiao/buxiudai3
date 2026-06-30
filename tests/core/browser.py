# -*- coding: utf-8 -*-
"""
浏览器管理 - 封装 Playwright 浏览器/上下文/页面

修复 P0-3: 提供 conftest.py 缺失的 browser fixture 替代实现（向后兼容）
"""
import os
import logging
from contextlib import contextmanager
from typing import Optional

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

logger = logging.getLogger(__name__)


# ==================== 浏览器配置 ====================
BROWSER_ARGS = [
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-dev-shm-usage',
    '--disable-gpu',
]


def create_browser(headless: Optional[bool] = None) -> Browser:
    """创建浏览器实例"""
    if headless is None:
        headless = os.getenv('HEADLESS', 'true').lower() == 'true'

    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=headless, args=BROWSER_ARGS)
    # 将 playwright 实例附加到 browser 供后续清理
    browser._pw_instance = pw
    return browser


def create_context(browser: Browser, **options) -> BrowserContext:
    """创建浏览器上下文"""
    defaults = {
        'viewport': {'width': 1920, 'height': 1080},
        'locale': 'zh-CN',
        'timezone_id': 'Asia/Shanghai',
        'ignore_https_errors': True,
    }
    defaults.update(options)
    return browser.new_context(**defaults)


def create_page(context: BrowserContext) -> Page:
    """创建页面"""
    page = context.new_page()
    page.set_default_timeout(15000)
    page.set_default_navigation_timeout(30000)
    return page


@contextmanager
def browser_session(headless: Optional[bool] = None, **context_options):
    """
    浏览器会话上下文管理器

    用法:
        with browser_session() as (browser, context, page):
            page.goto('...')
    """
    browser = create_browser(headless)
    try:
        context = create_context(browser, **context_options)
        try:
            page = create_page(context)
            yield browser, context, page
        finally:
            context.close()
    finally:
        # 关闭 playwright 实例
        if hasattr(browser, '_pw_instance'):
            browser._pw_instance.stop()
        browser.close()


def take_screenshot(page: Page, path: str, full_page: bool = True) -> str:
    """截图辅助"""
    try:
        page.screenshot(path=path, full_page=full_page, timeout=5000)
        logger.info(f"📸 截图保存: {path}")
        return path
    except Exception as e:
        logger.warning(f"截图失败: {e}")
        return ""


__all__ = [
    'BROWSER_ARGS',
    'create_browser', 'create_context', 'create_page',
    'browser_session', 'take_screenshot',
]
