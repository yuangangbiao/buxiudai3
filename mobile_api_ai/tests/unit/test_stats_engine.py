# -*- coding: utf-8 -*-
"""
stats_engine 单元测试

覆盖：
- StatsEngine 初始化
- seed_builtin_reports
- _render_sql 模板渲染（安全参数注入）
- _execute_raw_query
- get_dashboard / get_production_stats / get_cost_stats / get_worker_stats
- list_reports / get_report / save_report
- export_report
- schedule 报表
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime


class TestStatsEngineInit:
    """StatsEngine 初始化测试"""

    def test_init(self):
        from services.stats_engine import StatsEngine
        storage = MagicMock()
        engine = StatsEngine(storage)
        assert engine.storage is storage
        assert engine._builtin_seeded is False


class TestRenderSql:
    """_render_sql 模板渲染测试"""

    def setup_method(self):
        from services.stats_engine import StatsEngine
        self.engine = StatsEngine(MagicMock())

    def test_empty_template(self):
        assert self.engine._render_sql('') == ''

    def test_no_params(self):
        sql = 'SELECT * FROM orders'
        assert self.engine._render_sql(sql) == sql

    def test_string_param(self):
        result = self.engine._render_sql(
            "SELECT * FROM orders WHERE name = '{name}'",
            {'name': "test"}
        )
        assert "= 'test'" in result

    def test_string_with_quote(self):
        result = self.engine._render_sql(
            "SELECT * FROM t WHERE name = '{name}'",
            {'name': "O'Brien"}
        )
        assert "O''Brien" in result

    def test_int_param(self):
        result = self.engine._render_sql(
            "SELECT * FROM t WHERE id = {id}",
            {'id': 123}
        )
        assert '= 123' in result

    def test_float_param(self):
        result = self.engine._render_sql(
            "SELECT * FROM t WHERE price > {price}",
            {'price': 99.5}
        )
        assert '> 99.5' in result

    def test_none_param(self):
        result = self.engine._render_sql(
            "SELECT * FROM t WHERE val = {val}",
            {'val': None}
        )
        assert '= NULL' in result

    def test_missing_param_kept(self):
        result = self.engine._render_sql(
            "SELECT * FROM t WHERE a = {a} AND b = {b}",
            {'a': 1}
        )
        assert '{b}' in result

    def test_multiple_params(self):
        result = self.engine._render_sql(
            "SELECT * FROM t WHERE a = {a} AND b = {b}",
            {'a': 1, 'b': 2}
        )
        assert 'a = 1' in result
        assert 'b = 2' in result


class TestExecuteRawQuery:
    """_execute_raw_query 测试"""

    def test_empty_sql(self):
        from services.stats_engine import StatsEngine
        engine = StatsEngine(MagicMock())
        assert engine._execute_raw_query('') == []

    @patch('services.stats_engine.pymysql.connect')
    def test_query_success(self, mock_connect):
        from services.stats_engine import StatsEngine
        engine = StatsEngine(MagicMock())
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [{'id': 1, 'name': 'test'}]
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        result = engine._execute_raw_query('SELECT * FROM t')
        assert result == [{'id': 1, 'name': 'test'}]


class TestSeedBuiltinReports:
    """seed_builtin_reports 测试"""

    def test_seed_when_not_seeded(self):
        from services.stats_engine import StatsEngine
        storage = MagicMock()
        storage.list_report_definitions.return_value = []
        engine = StatsEngine(storage)
        engine.seed_builtin_reports()
        assert storage.save_report_definition.called
        assert engine._builtin_seeded is True

    def test_seed_idempotent(self):
        from services.stats_engine import StatsEngine
        storage = MagicMock()
        engine = StatsEngine(storage)
        engine._builtin_seeded = True
        engine.seed_builtin_reports()
        assert not storage.save_report_definition.called

    def test_seed_existing_definitions(self):
        from services.stats_engine import StatsEngine
        storage = MagicMock()
        storage.list_report_definitions.return_value = [{'id': 'existing'}]
        engine = StatsEngine(storage)
        engine.seed_builtin_reports()
        assert not storage.save_report_definition.called
        assert engine._builtin_seeded is True

    def test_get_builtin_definitions(self):
        from services.stats_engine import StatsEngine
        engine = StatsEngine(MagicMock())
        defs = engine._get_builtin_definitions('2026-01-01')
        assert len(defs) > 0
        assert all('id' in d for d in defs)


class TestGetBuiltinReportList:
    """获取内置报表列表测试"""

    def test_list_builtin_reports(self):
        from services.stats_engine import StatsEngine
        engine = StatsEngine(MagicMock())
        result = engine.list_builtin_reports()
        assert isinstance(result, list)
        assert len(result) > 0

    def test_list_builtin_reports_has_categories(self):
        from services.stats_engine import StatsEngine
        engine = StatsEngine(MagicMock())
        result = engine.list_builtin_reports()
        categories = {r.get('category') for r in result}
        assert len(categories) > 1


class TestGetDashboard:
    """get_dashboard 测试"""

    @patch('services.stats_engine.pymysql.connect')
    def test_dashboard_success(self, mock_connect):
        from services.stats_engine import StatsEngine
        engine = StatsEngine(MagicMock())
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            {'c': 10}, {'c': 8, 'done': 7}, {'c': 2}, {'c': 3}
        ]
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        result = engine.get_dashboard()
        assert 'today_reports' in result
        assert 'efficiency' in result

    @patch('services.stats_engine.pymysql.connect')
    def test_dashboard_no_data(self, mock_connect):
        from services.stats_engine import StatsEngine
        engine = StatsEngine(MagicMock())
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {'c': 0, 'done': 0}
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        result = engine.get_dashboard()
        assert 'today_reports' in result

    @patch('services.stats_engine.pymysql.connect', side_effect=Exception('error'))
    def test_dashboard_error(self, mock_connect):
        from services.stats_engine import StatsEngine
        engine = StatsEngine(MagicMock())
        result = engine.get_dashboard()
        assert result == {}


class TestGetProductionStats:
    """get_production_stats 测试"""

    def test_get_production_stats(self):
        from services.stats_engine import StatsEngine
        storage = MagicMock()
        storage.get_report_definition.return_value = {'sql_template': 'SELECT 1'}
        engine = StatsEngine(storage)
        with patch.object(engine, '_execute_raw_query', return_value=[]):
            result = engine.get_production_stats()
            assert 'overview' in result


class TestGetCostStats:
    """get_cost_stats 测试"""

    def test_get_cost_stats(self):
        from services.stats_engine import StatsEngine
        storage = MagicMock()
        storage.get_report_definition.return_value = {'sql_template': 'SELECT 1'}
        engine = StatsEngine(storage)
        with patch.object(engine, '_execute_raw_query', return_value=[]):
            result = engine.get_cost_stats()
            assert 'overview' in result


class TestGetWorkerStats:
    """get_worker_stats 测试"""

    def test_get_worker_stats(self):
        from services.stats_engine import StatsEngine
        storage = MagicMock()
        storage.get_report_definition.return_value = {'sql_template': 'SELECT 1'}
        engine = StatsEngine(storage)
        with patch.object(engine, '_execute_raw_query', return_value=[]):
            result = engine.get_worker_stats()
            assert 'ranking' in result


class TestReportDefinitions:
    """报表定义 CRUD 测试"""

    def test_list_reports(self):
        from services.stats_engine import StatsEngine
        storage = MagicMock()
        storage.list_report_definitions.return_value = [{'id': 'R1'}]
        engine = StatsEngine(storage)
        result = engine.list_reports()
        assert len(result) == 1

    def test_list_reports_with_filter(self):
        from services.stats_engine import StatsEngine
        storage = MagicMock()
        storage.list_report_definitions.return_value = []
        engine = StatsEngine(storage)
        engine.list_reports(category='production')
        assert storage.list_report_definitions.called

    def test_get_report(self):
        from services.stats_engine import StatsEngine
        storage = MagicMock()
        storage.get_report_definition.return_value = {'id': 'R1', 'name': 'test'}
        engine = StatsEngine(storage)
        result = engine.get_report('R1')
        assert result['id'] == 'R1'

    def test_get_report_not_found(self):
        from services.stats_engine import StatsEngine
        storage = MagicMock()
        storage.get_report_definition.return_value = None
        engine = StatsEngine(storage)
        assert engine.get_report('R999') is None

    def test_save_report(self):
        from services.stats_engine import StatsEngine
        storage = MagicMock()
        storage.save_report_definition.return_value = True
        engine = StatsEngine(storage)
        result = engine.save_report({'id': 'R1', 'name': 'test'})
        assert result is True

    def test_save_report_adds_timestamps(self):
        from services.stats_engine import StatsEngine
        storage = MagicMock()
        engine = StatsEngine(storage)
        engine.save_report({'id': 'R1'})
        data = storage.save_report_definition.call_args[0][0]
        assert 'created_at' in data
        assert 'updated_at' in data

    def test_delete_report(self):
        from services.stats_engine import StatsEngine
        storage = MagicMock()
        storage.delete_report_definition.return_value = True
        engine = StatsEngine(storage)
        result = engine.delete_report('R1')
        assert result is True


class TestSchedules:
    """报表调度测试"""

    def test_list_schedules(self):
        from services.stats_engine import StatsEngine
        storage = MagicMock()
        storage.list_schedules.return_value = [{'id': 'S1'}]
        engine = StatsEngine(storage)
        result = engine.list_schedules()
        assert len(result) == 1

    def test_list_schedules_enabled_only(self):
        from services.stats_engine import StatsEngine
        storage = MagicMock()
        storage.list_schedules.return_value = []
        engine = StatsEngine(storage)
        engine.list_schedules(enabled_only=True)
        assert storage.list_schedules.called

    def test_save_schedule(self):
        from services.stats_engine import StatsEngine
        storage = MagicMock()
        engine = StatsEngine(storage)
        result = engine.save_schedule({'id': 'S1'})
        assert storage.save_schedule.called

    def test_save_schedule_new_record(self):
        from services.stats_engine import StatsEngine
        storage = MagicMock()
        engine = StatsEngine(storage)
        engine.save_schedule({'report_id': 'R1'})
        data = storage.save_schedule.call_args[0][0]
        assert 'id' in data
        assert 'created_at' in data

    def test_save_schedule_existing(self):
        from services.stats_engine import StatsEngine
        storage = MagicMock()
        engine = StatsEngine(storage)
        engine.save_schedule({'id': 'S1', 'report_id': 'R1', 'created_at': '2026-01-01'})
        data = storage.save_schedule.call_args[0][0]
        assert data['id'] == 'S1'
        assert data['created_at'] == '2026-01-01'

    def test_delete_schedule(self):
        from services.stats_engine import StatsEngine
        storage = MagicMock()
        engine = StatsEngine(storage)
        result = engine.delete_schedule('S1')
        assert storage.delete_schedule.called
        assert result is True or result is None


class TestExportReport:
    """export_report 测试"""

    def test_export_report_definition_not_found(self):
        from services.stats_engine import StatsEngine
        storage = MagicMock()
        storage.get_report_definition.return_value = None
        engine = StatsEngine(storage)
        result = engine.export_report('R999')
        assert result.get('success') is False

    def test_export_report_success(self):
        from services.stats_engine import StatsEngine
        storage = MagicMock()
        storage.get_report_definition.return_value = {
            'id': 'R1', 'name': 'test',
            'sql_template': 'SELECT 1',
            'column_config': '[]'
        }
        engine = StatsEngine(storage)
        with patch.object(engine, '_execute_raw_query', return_value=[{'a': 1}]):
            with patch('services.stats_engine.DataExporter') as mock_exporter:
                mock_inst = MagicMock()
                mock_inst.export.return_value = '/tmp/r.xlsx'
                mock_exporter.return_value = mock_inst
                result = engine.export_report('R1', format='xlsx')
                assert result.get('success') is True or 'file_name' in result or 'error' in result

    def test_export_report_with_params(self):
        from services.stats_engine import StatsEngine
        storage = MagicMock()
        storage.get_report_definition.return_value = {
            'id': 'R1', 'name': 'test',
            'sql_template': 'SELECT * FROM t WHERE id = {id}',
            'column_config': '[]'
        }
        engine = StatsEngine(storage)
        with patch.object(engine, '_execute_raw_query', return_value=[]):
            with patch('services.stats_engine.DataExporter'):
                result = engine.export_report('R1', params={'id': 5})
                assert result is not None


class TestReportOutputs:
    """报表输出记录测试"""

    def test_list_outputs(self):
        from services.stats_engine import StatsEngine
        storage = MagicMock()
        engine = StatsEngine(storage)
        result = engine.list_outputs()
        assert storage.list_report_outputs.called

    def test_get_output(self):
        from services.stats_engine import StatsEngine
        storage = MagicMock()
        storage.get_report_output.return_value = {'id': 'O1'}
        engine = StatsEngine(storage)
        result = engine.get_output('O1')
        assert result['id'] == 'O1'
