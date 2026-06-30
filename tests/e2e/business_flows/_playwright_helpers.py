# -*- coding: utf-8 -*-
"""
Playwright UI 辅助模块 - 关键节点浏览器验证

使用场景:
- 移动端扫码报工 UI 验证
- 微信消息卡片点击验证

非关键场景不启用，避免拖慢测试速度。
"""
import os
import pytest


@pytest.fixture(scope='session')
def mobile_browser():
    """移动端浏览器 session"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip('Playwright 未安装，跳过 Playwright 测试')

    headless = os.getenv('PLAYWRIGHT_HEADLESS', 'true').lower() == 'true'
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            yield browser
            browser.close()
    except Exception as e:
        pytest.skip(f'Playwright 启动失败: {e}')


@pytest.fixture
def mobile_page(mobile_browser):
    """移动端页面 fixture"""
    context = mobile_browser.new_context(
        viewport={'width': 375, 'height': 667},  # iPhone 8 尺寸
        user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)',
    )
    page = context.new_page()
    yield page
    context.close()


def mobile_qr_scan(page, base_url: str, order_no: str, process_name: str, qty: int):
    """模拟扫码报工 UI 操作

    Args:
        page: Playwright page 对象
        base_url: 5008 移动端 base URL
        order_no: 工单号
        process_name: 工序名称
        qty: 报工数量

    Returns:
        dict: API 响应结果
    """
    # 1. 打开扫码报工页面
    page.goto(f'{base_url}/mobile/scan')

    # 2. 输入工单号
    page.fill('input[name="order_no"]', order_no)
    page.fill('input[name="process_name"]', process_name)
    page.fill('input[name="quantity"]', str(qty))

    # 3. 截图保存
    screenshot_path = f'tests/e2e/business_flows/screenshots/qr_scan_{order_no}.png'
    os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
    page.screenshot(path=screenshot_path)

    # 4. 提交
    page.click('button[type="submit"]')

    # 5. 等待响应
    page.wait_for_selector('.result-message', timeout=5000)

    # 6. 获取结果文本
    result_text = page.text_content('.result-message')

    return {
        'success': '成功' in result_text or 'success' in result_text.lower(),
        'message': result_text,
        'screenshot': screenshot_path,
    }


def wechat_message_click(page, message_url: str):
    """模拟点击微信消息卡片（占位实现）

    Args:
        page: Playwright page 对象
        message_url: 微信消息详情 URL
    """
    # 注：真实企业微信环境复杂，此处仅做占位
    # 实际项目可改用 mock 拦截
    page.goto(message_url)