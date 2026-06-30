# -*- coding: utf-8 -*-
"""补测 utils/log_scheduler.py"""
import pytest
from unittest.mock import patch, MagicMock, PropertyMock


class TestLogCleanupScheduler:
    """测试 LogCleanupScheduler"""

    def test_init(self):
        from utils.log_scheduler import LogCleanupScheduler
        s = LogCleanupScheduler()
        assert s.running is False
        assert s.thread is None

    def test_start_creates_daemon_thread(self):
        from utils.log_scheduler import LogCleanupScheduler
        s = LogCleanupScheduler()
        with patch('threading.Thread') as mock_thread_cls:
            mock_thread = MagicMock()
            mock_thread_cls.return_value = mock_thread
            s.start()
        assert s.running is True
        mock_thread_cls.assert_called_once_with(target=s._cleanup_task, daemon=True)
        mock_thread.start.assert_called_once()

    def test_start_idempotent(self):
        """第二次 start 不重复创建线程"""
        from utils.log_scheduler import LogCleanupScheduler
        s = LogCleanupScheduler()
        s.running = True
        with patch('threading.Thread') as mock_thread:
            s.start()
        mock_thread.assert_not_called()

    def test_stop_sets_running_false(self):
        from utils.log_scheduler import LogCleanupScheduler
        s = LogCleanupScheduler()
        s.running = True
        s.thread = MagicMock()
        s.stop()
        assert s.running is False
        s.thread.join.assert_called_once_with(timeout=5)

    def test_stop_no_thread(self):
        """stop 时 thread 为 None，不报错"""
        from utils.log_scheduler import LogCleanupScheduler
        s = LogCleanupScheduler()
        # Should not raise
        s.stop()
        assert s.running is False

    def test_cleanup_task_at_3am(self):
        """模拟凌晨3点触发清理"""
        from utils.log_scheduler import LogCleanupScheduler
        s = LogCleanupScheduler()
        s.running = True

        fake_now = MagicMock()
        fake_now.hour = 3
        fake_now.minute = 0
        fake_now.strftime.return_value = "2026-01-01 03:00:00"

        with patch('utils.log_scheduler.datetime') as mock_dt, \
             patch('utils.log_scheduler.OperationLogDAO') as mock_dao, \
             patch('utils.log_scheduler.time.sleep') as mock_sleep:
            mock_dt.now.return_value = fake_now
            mock_dao.clean_expired_logs.return_value = 10

            # Run one iteration then stop
            def fake_sleep(n):
                s.running = False
            mock_sleep.side_effect = fake_sleep

            s._cleanup_task()

        mock_dao.clean_expired_logs.assert_called_once()

    def test_cleanup_task_normal_hour(self):
        """非凌晨3点不触发清理"""
        from utils.log_scheduler import LogCleanupScheduler
        s = LogCleanupScheduler()
        s.running = True

        fake_now = MagicMock()
        fake_now.hour = 14
        fake_now.minute = 30

        with patch('utils.log_scheduler.datetime') as mock_dt, \
             patch('utils.log_scheduler.time.sleep') as mock_sleep:
            mock_dt.now.return_value = fake_now

            def fake_sleep(n):
                s.running = False
            mock_sleep.side_effect = fake_sleep

            s._cleanup_task()

        # No cleanup call when not 3am

    def test_cleanup_task_exception(self):
        """清理抛异常时被捕获"""
        from utils.log_scheduler import LogCleanupScheduler
        s = LogCleanupScheduler()
        s.running = True

        fake_now = MagicMock()
        fake_now.hour = 3
        fake_now.minute = 0
        fake_now.strftime.return_value = "2026-01-01 03:00:00"

        with patch('utils.log_scheduler.datetime') as mock_dt, \
             patch('utils.log_scheduler.OperationLogDAO') as mock_dao, \
             patch('utils.log_scheduler.time.sleep') as mock_sleep:
            mock_dt.now.return_value = fake_now
            mock_dao.clean_expired_logs.side_effect = Exception("DB connection failed")

            def fake_sleep(n):
                s.running = False
            mock_sleep.side_effect = fake_sleep

            # Should not raise
            s._cleanup_task()


class TestModuleFunctions:
    """测试模块级函数"""

    def test_start_log_cleanup_scheduler(self):
        from utils.log_scheduler import log_scheduler
        with patch.object(log_scheduler, 'start') as mock_start:
            from utils.log_scheduler import start_log_cleanup_scheduler
            start_log_cleanup_scheduler()
            mock_start.assert_called_once()

    def test_stop_log_cleanup_scheduler(self):
        from utils.log_scheduler import log_scheduler
        with patch.object(log_scheduler, 'stop') as mock_stop:
            from utils.log_scheduler import stop_log_cleanup_scheduler
            stop_log_cleanup_scheduler()
            mock_stop.assert_called_once()
