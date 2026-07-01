# -*- coding: utf-8 -*-
"""
scheduler 单元测试

覆盖：
- ReportScheduler 初始化
- start/stop
- is_running
- _is_due 各种 cron 表达式
- _execute_schedule 成功/失败
- get_scheduler 单例
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta


class TestReportSchedulerInit:
    """ReportScheduler 初始化测试"""

    def test_init(self):
        from services.scheduler import ReportScheduler
        engine = MagicMock()
        scheduler = ReportScheduler(engine, check_interval=30)
        assert scheduler.engine is engine
        assert scheduler.check_interval == 30
        assert scheduler._running is False
        assert scheduler._thread is None

    def test_default_check_interval(self):
        from services.scheduler import ReportScheduler
        engine = MagicMock()
        scheduler = ReportScheduler(engine)
        assert scheduler.check_interval == 60


class TestReportSchedulerLifecycle:
    """生命周期测试"""

    def test_start_creates_thread(self):
        from services.scheduler import ReportScheduler
        engine = MagicMock()
        scheduler = ReportScheduler(engine, check_interval=1)
        scheduler.start()
        assert scheduler._thread is not None
        scheduler.stop()

    def test_start_already_running(self):
        from services.scheduler import ReportScheduler
        engine = MagicMock()
        scheduler = ReportScheduler(engine, check_interval=1)
        scheduler.start()
        thread = scheduler._thread
        scheduler.start()
        assert scheduler._thread is thread
        scheduler.stop()

    def test_stop_sets_running_false(self):
        from services.scheduler import ReportScheduler
        engine = MagicMock()
        scheduler = ReportScheduler(engine, check_interval=1)
        scheduler.start()
        scheduler.stop()
        assert scheduler._running is False

    def test_is_running_false_initially(self):
        from services.scheduler import ReportScheduler
        engine = MagicMock()
        scheduler = ReportScheduler(engine)
        assert scheduler.is_running() is False

    def test_is_running_true_after_start(self):
        from services.scheduler import ReportScheduler
        engine = MagicMock()
        scheduler = ReportScheduler(engine, check_interval=1)
        scheduler.start()
        assert scheduler.is_running() is True
        scheduler.stop()


class TestIsDue:
    """_is_due 测试"""

    def test_no_last_run_is_due(self):
        from services.scheduler import ReportScheduler
        engine = MagicMock()
        scheduler = ReportScheduler(engine)
        schedule = {'id': '1', 'cron_expression': 'daily', 'last_run_at': None}
        now = datetime.now()
        assert scheduler._is_due(schedule, now) is True

    def test_hourly_not_due(self):
        from services.scheduler import ReportScheduler
        engine = MagicMock()
        scheduler = ReportScheduler(engine)
        now = datetime.now()
        schedule = {
            'id': '1', 'cron_expression': 'hourly',
            'last_run_at': (now - timedelta(minutes=30)).isoformat()
        }
        assert scheduler._is_due(schedule, now) is False

    def test_hourly_due(self):
        from services.scheduler import ReportScheduler
        engine = MagicMock()
        scheduler = ReportScheduler(engine)
        now = datetime.now()
        schedule = {
            'id': '1', 'cron_expression': 'hourly',
            'last_run_at': (now - timedelta(hours=2)).isoformat()
        }
        assert scheduler._is_due(schedule, now) is True

    def test_daily_due_next_day(self):
        from services.scheduler import ReportScheduler
        engine = MagicMock()
        scheduler = ReportScheduler(engine)
        now = datetime.now()
        schedule = {
            'id': '1', 'cron_expression': 'daily',
            'last_run_at': (now - timedelta(days=2)).isoformat()
        }
        assert scheduler._is_due(schedule, now) is True

    def test_daily_not_due_same_day(self):
        from services.scheduler import ReportScheduler
        engine = MagicMock()
        scheduler = ReportScheduler(engine)
        now = datetime(2026, 5, 30, 12, 0, 0)
        schedule = {
            'id': '1', 'cron_expression': 'daily',
            'last_run_at': datetime(2026, 5, 30, 8, 0, 0).isoformat()
        }
        assert scheduler._is_due(schedule, now) is False

    def test_weekly_due(self):
        from services.scheduler import ReportScheduler
        engine = MagicMock()
        scheduler = ReportScheduler(engine)
        now = datetime.now()
        schedule = {
            'id': '1', 'cron_expression': 'weekly',
            'last_run_at': (now - timedelta(days=10)).isoformat()
        }
        assert scheduler._is_due(schedule, now) is True

    def test_weekly_not_due(self):
        from services.scheduler import ReportScheduler
        engine = MagicMock()
        scheduler = ReportScheduler(engine)
        now = datetime.now()
        schedule = {
            'id': '1', 'cron_expression': 'weekly',
            'last_run_at': (now - timedelta(days=3)).isoformat()
        }
        assert scheduler._is_due(schedule, now) is False

    def test_monthly_due(self):
        from services.scheduler import ReportScheduler
        engine = MagicMock()
        scheduler = ReportScheduler(engine)
        now = datetime.now()
        schedule = {
            'id': '1', 'cron_expression': 'monthly',
            'last_run_at': (now - timedelta(days=30)).isoformat()
        }
        assert scheduler._is_due(schedule, now) is True

    def test_every_30min_due(self):
        from services.scheduler import ReportScheduler
        engine = MagicMock()
        scheduler = ReportScheduler(engine)
        now = datetime.now()
        schedule = {
            'id': '1', 'cron_expression': 'every_30min',
            'last_run_at': (now - timedelta(minutes=45)).isoformat()
        }
        assert scheduler._is_due(schedule, now) is True

    def test_unknown_cron_not_due(self):
        from services.scheduler import ReportScheduler
        engine = MagicMock()
        scheduler = ReportScheduler(engine)
        now = datetime.now()
        schedule = {
            'id': '1', 'cron_expression': 'unknown_cron',
            'last_run_at': (now - timedelta(days=30)).isoformat()
        }
        assert scheduler._is_due(schedule, now) is False


class TestExecuteSchedule:
    """_execute_schedule 测试"""

    def test_execute_success(self):
        from services.scheduler import ReportScheduler
        engine = MagicMock()
        engine.export_report.return_value = {
            'success': True, 'file_name': 'report.xlsx'
        }
        scheduler = ReportScheduler(engine)
        schedule = {
            'id': '1',
            'report_id': 'R001',
            'name': '日报',
            'cron_expression': 'daily',
            'params': '{"key": "value"}',
            'export_profile_id': '',
            'export_format': 'xlsx'
        }
        scheduler._execute_schedule(schedule)
        assert engine.export_report.called
        assert engine.save_schedule.called

    def test_execute_failure(self):
        from services.scheduler import ReportScheduler
        engine = MagicMock()
        engine.export_report.return_value = {
            'success': False, 'error': '测试错误'
        }
        engine.storage.save_report_output.return_value = True
        scheduler = ReportScheduler(engine)
        schedule = {
            'id': '1', 'report_id': 'R001', 'name': '日报',
            'cron_expression': 'daily', 'params': '{}',
            'export_format': 'xlsx'
        }
        scheduler._execute_schedule(schedule)
        assert engine.storage.save_report_output.called

    def test_execute_with_profile_id(self):
        from services.scheduler import ReportScheduler
        engine = MagicMock()
        engine.export_report.return_value = {'success': True, 'file_name': 'r.xlsx'}
        scheduler = ReportScheduler(engine)
        schedule = {
            'id': '1', 'report_id': 'R001', 'name': 'test',
            'cron_expression': 'daily', 'params': '{}',
            'export_profile_id': 'P001', 'export_format': 'pdf'
        }
        scheduler._execute_schedule(schedule)
        kwargs = engine.export_report.call_args.kwargs
        assert kwargs['profile_id'] == 'P001'
        assert kwargs['format'] == 'pdf'

    def test_execute_invalid_json_params(self):
        from services.scheduler import ReportScheduler
        engine = MagicMock()
        engine.export_report.return_value = {'success': True, 'file_name': 'r.xlsx'}
        scheduler = ReportScheduler(engine)
        schedule = {
            'id': '1', 'report_id': 'R001', 'name': 'test',
            'cron_expression': 'daily', 'params': 'invalid json{',
            'export_format': 'xlsx'
        }
        scheduler._execute_schedule(schedule)
        assert engine.export_report.called


class TestCheckSchedules:
    """_check_schedules 测试"""

    def test_check_empty(self):
        from services.scheduler import ReportScheduler
        engine = MagicMock()
        engine.list_schedules.return_value = []
        scheduler = ReportScheduler(engine)
        scheduler._check_schedules()
        assert engine.list_schedules.called

    def test_check_executes_due(self):
        from services.scheduler import ReportScheduler
        engine = MagicMock()
        engine.list_schedules.return_value = [{
            'id': '1', 'cron_expression': 'daily', 'last_run_at': None,
            'report_id': 'R001', 'name': 'test', 'params': '{}',
            'export_format': 'xlsx'
        }]
        engine.export_report.return_value = {'success': True, 'file_name': 'r.xlsx'}
        scheduler = ReportScheduler(engine)
        scheduler._check_schedules()
        assert engine.export_report.called

    def test_check_skips_not_due(self):
        from services.scheduler import ReportScheduler
        engine = MagicMock()
        now = datetime.now()
        engine.list_schedules.return_value = [{
            'id': '1', 'cron_expression': 'daily',
            'last_run_at': now.isoformat(),
            'report_id': 'R001', 'name': 'test',
            'params': '{}', 'export_format': 'xlsx'
        }]
        scheduler = ReportScheduler(engine)
        scheduler._check_schedules()
        assert not engine.export_report.called

    def test_check_continues_after_error(self):
        from services.scheduler import ReportScheduler
        engine = MagicMock()
        engine.list_schedules.side_effect = Exception('error')
        scheduler = ReportScheduler(engine)
        with patch('services.scheduler.logger'):
            scheduler._check_schedules()


class TestGetScheduler:
    """get_scheduler 单例测试"""

    def teardown_method(self):
        import services.scheduler as m
        m._scheduler_instance = None

    def test_get_scheduler_returns_none_without_engine(self):
        import services.scheduler as m
        m._scheduler_instance = None
        result = m.get_scheduler()
        assert result is None

    def test_get_scheduler_creates_with_engine(self):
        import services.scheduler as m
        m._scheduler_instance = None
        engine = MagicMock()
        result = m.get_scheduler(engine)
        assert result is not None
        assert result.engine is engine

    def test_get_scheduler_singleton(self):
        import services.scheduler as m
        m._scheduler_instance = None
        engine = MagicMock()
        s1 = m.get_scheduler(engine)
        s2 = m.get_scheduler()
        assert s1 is s2


class TestStartScheduler:
    """start_scheduler 测试"""

    def test_start_scheduler(self):
        import services.scheduler as m
        m._scheduler_instance = None
        engine = MagicMock()
        s = m.start_scheduler(engine, check_interval=1)
        assert s is not None
        assert s.is_running() is True
        s.stop()
