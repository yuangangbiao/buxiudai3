# -*- coding: utf-8 -*-
"""
移动端任务页 - Page Object
"""
import logging
from tests.pages.base_page import BasePage

logger = logging.getLogger(__name__)


class MobileTasksPage(BasePage):
    """5008 我的任务页"""

    SELECTORS = {
        'task_list': '.task-list, [data-test="tasks"]',
        'task_card': '.task-card, .task-item',
        'task_title': '.task-title, h3',
        'report_btn': 'button.report, [data-action="report"]',
        'qty_input': 'input[name="qty"], #qty',
    }

    def goto_list(self):
        self.goto('/tasks')
        self.wait_for(self.SELECTORS['task_list'])
        return self

    def get_task_titles(self) -> list:
        cards = self.page.locator(self.SELECTORS['task_card']).all()
        return [c.locator(self.SELECTORS['task_title']).first.text_content().strip() for c in cards]

    def report(self, task_title: str, qty: int):
        """报工"""
        card = self.page.locator(self.SELECTORS['task_card']).filter(has_text=task_title).first
        card.locator(self.SELECTORS['report_btn']).click()
        self.fill(self.SELECTORS['qty_input'], str(qty))
        return self
