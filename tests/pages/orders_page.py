# -*- coding: utf-8 -*-
"""
订单管理页 - Page Object
"""
import logging
from tests.pages.base_page import BasePage

logger = logging.getLogger(__name__)


class OrdersPage(BasePage):
    """5001 订单列表/详情页"""

    SELECTORS = {
        'order_list': 'table.orders, .order-list, [data-test="orders"]',
        'order_row': 'table.orders tbody tr, .order-item',
        'order_no': 'td.order-no, .order-no, [data-field="order_no"]',
        'search_input': 'input[name="search"], input[type="search"], #search',
        'create_btn': 'button.create-order, a.create-order, [data-action="create"]',
        'status_filter': 'select[name="status"], #status-filter',
        'next_page': '.pagination .next, a.next',
    }

    def goto_list(self):
        """进入订单列表"""
        self.goto('/orders')
        self.wait_for(self.SELECTORS['order_list'])
        return self

    def search(self, keyword: str):
        """搜索订单"""
        self.fill(self.SELECTORS['search_input'], keyword)
        return self

    def click_create(self):
        """点击新建订单"""
        self.click(self.SELECTORS['create_btn'])
        return self

    def filter_by_status(self, status: str):
        """按状态筛选"""
        self.page.select_option(self.SELECTORS['status_filter'], status)
        return self

    def get_order_nos(self) -> list:
        """获取订单号列表"""
        rows = self.page.locator(self.SELECTORS['order_row']).all()
        order_nos = []
        for row in rows:
            no_cell = row.locator(self.SELECTORS['order_no']).first
            if no_cell.is_visible():
                order_nos.append(no_cell.text_content().strip())
        return order_nos

    def open_order(self, order_no: str):
        """打开指定订单"""
        row = self.page.locator(self.SELECTORS['order_row']).filter(has_text=order_no).first
        row.click()
        return self
