# -*- coding: utf-8 -*-
"""C1-C3 修复测试 — 补充覆盖"""
import pytest
from unittest.mock import patch, MagicMock


class TestStorageMethods:
    """C2: storage 新函数可导入"""

    def test_save_history_importable(self):
        from storage.mysql_storage import MySQLStorage
        assert hasattr(MySQLStorage, 'save_history')

    def test_soft_delete_importable(self):
        from storage.mysql_storage import MySQLStorage
        assert hasattr(MySQLStorage, 'soft_delete_sub_step')

    def test_get_history_importable(self):
        from storage.mysql_storage import MySQLStorage
        assert hasattr(MySQLStorage, 'get_history')

    def test_get_first_created_at_importable(self):
        from storage.mysql_storage import MySQLStorage
        assert hasattr(MySQLStorage, 'get_first_created_at')

    def test_wal_write_importable(self):
        from storage.mysql_storage import MySQLStorage
        assert hasattr(MySQLStorage, 'wal_write')

    def test_wal_replay_importable(self):
        from storage.mysql_storage import MySQLStorage
        assert hasattr(MySQLStorage, 'wal_replay')


class TestRetryQueueImport:
    """C3: retry_queue 可导入"""

    def test_enqueue_importable(self):
        from retry_queue import enqueue_retry, process_retry_queue
        assert callable(enqueue_retry)
        assert callable(process_retry_queue)


class TestNotifyImport:
    """C3: notify 可导入"""

    def test_notify_importable(self):
        from notify import send_notification, notify_override
        assert callable(send_notification)
        assert callable(notify_override)


class TestRegressionInit:
    """回归模块入口完整"""

    def test_regression_init_exports(self):
        from regression import decide_regression, REGRESSION_ACTIONS
        assert callable(decide_regression)
        assert 'insert' in REGRESSION_ACTIONS
        assert 'prompt' in REGRESSION_ACTIONS
        assert 'reject_timeout' in REGRESSION_ACTIONS
