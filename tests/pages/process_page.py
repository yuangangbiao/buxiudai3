# -*- coding: utf-8 -*-
"""
工序管理页 - Page Object
"""
import logging
from tests.pages.base_page import BasePage

logger = logging.getLogger(__name__)


class ProcessPage(BasePage):
    """工序任务管理页"""

    SELECTORS = {
        'task_list': 'table.process-tasks, .task-list',
        'task_row': 'table.process-tasks tbody tr, .task-item',
        'process_code': 'td.process-code, .process-code',
        'start_btn': 'button.start-task, [data-action="start"]',
        'complete_btn': 'button.complete-task, [data-action="complete"]',
        'progress_bar': '.progress-bar, [role="progressbar"]',
    }

    def goto_list(self):
        self.goto('/process')
        self.wait_for(self.SELECTORS['task_list'])
        return self

    def start_task(self, task_id: str):
        """开始任务"""
        row = self.page.locator(self.SELECTORS['task_row']).filter(has_text=task_id).first
        row.locator(self.SELECTORS['start_btn']).click()
        return self

    def complete_task(self, task_id: str, qty: int):
        """完成任务"""
        row = self.page.locator(self.SELECTORS['task_row']).filter(has_text=task_id).first
        row.locator(self.SELECTORS['complete_btn']).click()
        return self
