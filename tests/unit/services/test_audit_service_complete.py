# -*- coding: utf-8 -*-
"""
services/audit_service.py 测试 - 当前74%，提升到90%+
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


class TestAuditServiceConstants:
    """审计常量测试"""

    def test_action_constants(self):
        from services.audit_service import AuditService
        assert AuditService.ACTION_CREATE == 'CREATE'
        assert AuditService.ACTION_UPDATE == 'UPDATE'
        assert AuditService.ACTION_DELETE == 'DELETE'
        assert AuditService.ACTION_STATUS_CHANGE == 'STATUS_CHANGE'
        assert AuditService.ACTION_LOGIN == 'LOGIN'
        assert AuditService.ACTION_LOGOUT == 'LOGOUT'
        assert AuditService.ACTION_IMPORT == 'IMPORT'
        assert AuditService.ACTION_EXPORT == 'EXPORT'

    def test_entity_constants(self):
        from services.audit_service import AuditService
        assert AuditService.ENTITY_ORDER == 'ORDER'
        assert AuditService.ENTITY_INVENTORY == 'INVENTORY'
        assert AuditService.ENTITY_PROCESS == 'PROCESS'
        assert AuditService.ENTITY_OPERATOR == 'OPERATOR'
        assert AuditService.ENTITY_BOM == 'BOM'
        assert AuditService.ENTITY_ALERT == 'ALERT'


class TestAuditServiceGetLogs:
    """get_logs 条件分支测试 - 覆盖 L154-171"""

    @patch('services.audit_service.get_connection')
    def test_get_logs_no_conditions(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.description = [('id',), ('timestamp',), ('operator',), ('action',), ('entity_type',), ('entity_id',), ('before_data',), ('after_data',), ('remark',), ('ip_address',), ('extra_info',)]
        mock_cursor.fetchall.return_value = []
        mock_conn.return_value.cursor.return_value = mock_cursor

        from services.audit_service import AuditService
        AuditService._ensure_table = MagicMock()
        result = AuditService.get_logs()
        assert isinstance(result, list)

    @patch('services.audit_service.get_connection')
    def test_get_logs_with_entity_type(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.description = [('id',), ('timestamp',), ('operator',), ('action',), ('entity_type',), ('entity_id',), ('before_data',), ('after_data',), ('remark',), ('ip_address',), ('extra_info',)]
        mock_cursor.fetchall.return_value = [(1, '2026-05-29', 'admin', 'CREATE', 'ORDER', '123', None, None, None, None, None)]
        mock_conn.return_value.cursor.return_value = mock_cursor

        from services.audit_service import AuditService
        AuditService._ensure_table = MagicMock()
        result = AuditService.get_logs(entity_type='ORDER')
        assert len(result) == 1
        assert result[0]['entity_type'] == 'ORDER'

    @patch('services.audit_service.get_connection')
    def test_get_logs_with_multiple_filters(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.description = [('id',), ('timestamp',), ('operator',), ('action',), ('entity_type',), ('entity_id',), ('before_data',), ('after_data',), ('remark',), ('ip_address',), ('extra_info',)]
        mock_cursor.fetchall.return_value = []
        mock_conn.return_value.cursor.return_value = mock_cursor

        from services.audit_service import AuditService
        AuditService._ensure_table = MagicMock()
        result = AuditService.get_logs(
            entity_type='ORDER',
            entity_id='123',
            action='CREATE',
            operator='admin',
            start_date='2026-05-01',
            end_date='2026-05-29',
            limit=50,
            offset=10
        )
        assert isinstance(result, list)


class TestAuditServiceGetEntityHistory:
    """get_entity_history 测试 - 覆盖 L188-190"""

    @patch('services.audit_service.AuditService.get_logs')
    def test_get_entity_history(self, mock_get_logs):
        mock_get_logs.return_value = [{'id': 1}]
        from services.audit_service import AuditService
        result = AuditService.get_entity_history('ORDER', '123')
        mock_get_logs.assert_called_once_with(entity_type='ORDER', entity_id='123')
        assert result == [{'id': 1}]


class TestAuditServiceGetOperatorLogs:
    """get_operator_logs 测试 - 覆盖 L193-195"""

    @patch('services.audit_service.AuditService.get_logs')
    def test_get_operator_logs(self, mock_get_logs):
        mock_get_logs.return_value = [{'id': 1}]
        from services.audit_service import AuditService
        result = AuditService.get_operator_logs('admin', limit=50)
        mock_get_logs.assert_called_once_with(operator='admin', limit=50)
        assert result == [{'id': 1}]


class TestAuditServiceGetRecentLogs:
    """get_recent_logs 测试 - 覆盖 L198-201"""

    @patch('services.audit_service.AuditService.get_logs')
    def test_get_recent_logs(self, mock_get_logs):
        mock_get_logs.return_value = []
        from services.audit_service import AuditService
        result = AuditService.get_recent_logs(hours=48, limit=100)
        mock_get_logs.assert_called_once()
        # 检查 start_time 参数
        call_kwargs = mock_get_logs.call_args[1]
        assert 'start_date' in call_kwargs
        assert call_kwargs['limit'] == 100


class TestAuditServiceClearOldLogs:
    """clear_old_logs 测试 - 覆盖 L204-223"""

    @patch('services.audit_service.get_connection')
    def test_clear_old_logs(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 5
        mock_conn.return_value.cursor.return_value = mock_cursor
        mock_conn.return_value.commit.return_value = None

        from services.audit_service import AuditService
        AuditService._ensure_table = MagicMock()
        deleted = AuditService.clear_old_logs(days=90)
        assert deleted == 5

    @patch('services.audit_service.get_connection')
    def test_clear_old_logs_zero(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 0
        mock_conn.return_value.cursor.return_value = mock_cursor

        from services.audit_service import AuditService
        AuditService._ensure_table = MagicMock()
        deleted = AuditService.clear_old_logs(days=1)
        assert deleted == 0


class TestAuditServiceLogException:
    """log 异常分支测试 - 覆盖 L111-122"""

    @patch('services.audit_service.get_connection')
    @patch('services.audit_service.logger')
    def test_log_db_error(self, mock_logger, mock_conn):
        mock_conn.return_value.cursor.side_effect = Exception("DB connection failed")

        from services.audit_service import AuditService
        result = AuditService.log('CREATE', 'ORDER', entity_id='123')
        assert result is False
        mock_logger.error.assert_called_once()


class TestAuditServiceEnsureTable:
    """_ensure_table 通过其他测试间接覆盖"""
    pass


class TestAuditLogFunction:
    """audit_log 便捷函数测试 - 覆盖 L226-228"""

    @patch('services.audit_service.AuditService.log')
    def test_audit_log_function(self, mock_log):
        mock_log.return_value = True
        from services.audit_service import audit_log
        result = audit_log('CREATE', 'ORDER', entity_id='123')
        mock_log.assert_called_once_with('CREATE', 'ORDER', entity_id='123')
        assert result is True
