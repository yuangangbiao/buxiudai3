# -*- coding: utf-8 -*-
"""
质检管理页 - Page Object
"""
import logging
from tests.pages.base_page import BasePage

logger = logging.getLogger(__name__)


class QualityPage(BasePage):
    """质检管理页"""

    SELECTORS = {
        'inspection_list': 'table.quality-inspections, .inspection-list',
        'inspection_row': 'table.quality-inspections tbody tr, .inspection-item',
        'pass_btn': 'button.pass-quality, [data-result="pass"]',
        'fail_btn': 'button.fail-quality, [data-result="fail"]',
        'defect_input': 'textarea[name="defect"], input[name="defect"]',
        'submit_btn': 'button[type="submit"]',
    }

    def goto_list(self):
        self.goto('/quality')
        self.wait_for(self.SELECTORS['inspection_list'])
        return self

    def mark_pass(self, inspection_id: str):
        """标记合格"""
        row = self.page.locator(self.SELECTORS['inspection_row']).filter(has_text=inspection_id).first
        row.locator(self.SELECTORS['pass_btn']).click()
        return self

    def mark_fail(self, inspection_id: str, defect: str):
        """标记不合格"""
        row = self.page.locator(self.SELECTORS['inspection_row']).filter(has_text=inspection_id).first
        row.locator(self.SELECTORS['fail_btn']).click()
        self.fill(self.SELECTORS['defect_input'], defect)
        self.click(self.SELECTORS['submit_btn'])
        return self
