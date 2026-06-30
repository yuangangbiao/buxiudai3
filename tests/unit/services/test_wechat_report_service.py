# -*- coding: utf-8 -*-
"""
Unit tests for services/wechat_report_service.py — WeChatReportService

Covers all public and private methods including:
_ensure_tables, _get_container_url, publish_task_to_operator,
_start_queue_processor, _process_queue, _send_task,
process_callback, sync_report_status, batch_update_status,
update_operator, get_dead_tasks, retry_dead_task
"""
import json

import pytest
import requests
from unittest.mock import patch, MagicMock, call, ANY, PropertyMock


# ------------------------------------------------------------------ #
#  Fixtures
# ------------------------------------------------------------------ #

@pytest.fixture(autouse=True)
def reset_class_state():
    """Reset class-level state before each test."""
    from services.wechat_report_service import WeChatReportService
    WeChatReportService._queue_processor_started = False


@pytest.fixture
def mock_conn():
    """Create a mock DB connection with attached cursor."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor


def _make_record(**overrides):
    """Helper to create a dict mimicking a MySQL row (DictCursor)."""
    base = {
        'id': 1, 'status': '待开始', 'prod_id': 10, 'order_id': 100,
        'process_name': '冲压', 'process_seq': 1,
        'completed_qty': 0, 'qualified_qty': 0, 'worker': None,
        'work_hours': 0, 'start_time': None, 'end_time': None,
        'record_date': None, 'publish_status': 'none',
    }
    base.update(overrides)
    return base


# ===================================================================
#  _ensure_tables
# ===================================================================

class TestEnsureTables:
    """Cover _ensure_tables — table creation & migration"""

    def test_table_not_exists_creates(self, mock_conn):
        """When SHOW TABLES returns no rows, CREATE TABLE is executed."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        cursor.fetchone.side_effect = [None]  # table not found

        with patch('services.wechat_report_service.get_connection', return_value=conn):
            WeChatReportService._ensure_tables()

        # Should execute SHOW TABLES, then CREATE TABLE
        create_calls = [
            c for c in cursor.execute.call_args_list
            if 'CREATE TABLE' in str(c)
        ]
        assert len(create_calls) == 1
        conn.commit.assert_called()

    def test_table_exists_skip_create(self, mock_conn):
        """When SHOW TABLES returns a row, CREATE TABLE is skipped."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        # table found, then 'last_retry_at' column found, then uk_order_process key found
        cursor.fetchone.side_effect = [True, True, True]

        with patch('services.wechat_report_service.get_connection', return_value=conn):
            WeChatReportService._ensure_tables()

        # No CREATE TABLE statement should be seen
        create_calls = [
            c for c in cursor.execute.call_args_list
            if 'CREATE TABLE' in str(c)
        ]
        assert len(create_calls) == 0

    def test_table_exists_missing_last_retry_at_adds_column(self, mock_conn):
        """When table exists but last_retry_at column is missing, ALTER is executed."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        # table found, last_retry_at column NOT found, uk key found
        cursor.fetchone.side_effect = [True, None, True]

        with patch('services.wechat_report_service.get_connection', return_value=conn):
            WeChatReportService._ensure_tables()

        alter_calls = [
            c for c in cursor.execute.call_args_list
            if 'ALTER TABLE' in str(c)
        ]
        assert len(alter_calls) == 1
        assert 'ADD COLUMN last_retry_at' in str(alter_calls[0])

    def test_table_exists_missing_unique_key(self, mock_conn):
        """When table exists but uk_order_process key is missing, ALTER is executed."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        # table found, last_retry_at found, uk key NOT found
        cursor.fetchone.side_effect = [True, True, None]

        with patch('services.wechat_report_service.get_connection', return_value=conn):
            WeChatReportService._ensure_tables()

        alter_calls = [
            c for c in cursor.execute.call_args_list
            if 'ADD UNIQUE KEY' in str(c)
        ]
        assert len(alter_calls) == 1
        assert 'uk_order_process' in str(alter_calls[0])

    def test_table_exception_rollback(self, mock_conn):
        """When an exception occurs, rollback is called."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        cursor.execute.side_effect = Exception("DB error")

        with patch('services.wechat_report_service.get_connection', return_value=conn):
            WeChatReportService._ensure_tables()

        conn.rollback.assert_called_once()
        cursor.close.assert_called_once()
        conn.close.assert_called_once()


# ===================================================================
#  _get_container_url
# ===================================================================

class TestGetContainerUrl:
    """Cover _get_container_url — environment variable fallback"""

    def test_returns_env_var(self):
        """When CONTAINER_URL is set, return its value."""
        from services.wechat_report_service import WeChatReportService
        with patch('services.wechat_report_service.os.getenv',
                   return_value='http://test-url:8888'):
            url = WeChatReportService._get_container_url()
        assert url == 'http://test-url:8888'

    def test_default_fallback(self):
        """When CONTAINER_URL is not set, return default."""
        from services.wechat_report_service import WeChatReportService
        with patch('services.wechat_report_service.os.getenv',
                   return_value='http://localhost:5002'):
            url = WeChatReportService._get_container_url()
        assert url == 'http://localhost:5002'


# ===================================================================
#  publish_task_to_operator
# ===================================================================

class TestPublishTaskToOperator:
    """Cover publish_task_to_operator — task queuing"""

    def test_publish_success(self, mock_conn):
        """Successful insert with new task."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        cursor.rowcount = 1
        cursor.lastrowid = 42

        with patch('services.wechat_report_service.get_connection', return_value=conn):
            with patch.object(WeChatReportService, '_ensure_tables') as mock_ensure:
                with patch.object(WeChatReportService, '_start_queue_processor') as mock_start:
                    result = WeChatReportService.publish_task_to_operator(
                        {'order_no': 'ORD-001', 'process_name': '冲压', 'qty': 50},
                        'OP001'
                    )

        assert result['success'] is True
        assert result['task_id'] == 42
        mock_ensure.assert_called_once()
        mock_start.assert_called_once()

    def test_publish_duplicate_pending(self, mock_conn):
        """Existing pending task returns message without re-insert."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        cursor.rowcount = 0  # no rows inserted due to duplicate
        # Simulate existing task with pending status
        cursor.fetchone.return_value = {'id': 1, 'status': 'pending'}

        with patch('services.wechat_report_service.get_connection', return_value=conn):
            with patch.object(WeChatReportService, '_ensure_tables'):
                with patch.object(WeChatReportService, '_start_queue_processor'):
                    result = WeChatReportService.publish_task_to_operator(
                        {'order_no': 'ORD-001', 'process_name': '冲压'},
                        'OP001'
                    )

        assert result['success'] is True
        assert result['task_id'] == 1
        assert '已在发送队列' in result['message']

    def test_publish_duplicate_already_done(self, mock_conn):
        """Existing success task returns 'already exists' message."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        cursor.rowcount = 0
        cursor.fetchone.return_value = {'id': 2, 'status': 'success'}

        with patch('services.wechat_report_service.get_connection', return_value=conn):
            with patch.object(WeChatReportService, '_ensure_tables'):
                result = WeChatReportService.publish_task_to_operator(
                    {'order_no': 'ORD-001', 'process_name': '冲压'},
                    'OP001'
                )

        assert result['success'] is True
        assert '无需重复入队' in result['message']

    def test_publish_exception(self, mock_conn):
        """DB exception returns failure."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        cursor.execute.side_effect = Exception("Connection lost")

        with patch('services.wechat_report_service.get_connection', return_value=conn):
            with patch.object(WeChatReportService, '_ensure_tables'):
                result = WeChatReportService.publish_task_to_operator(
                    {'order_no': 'ORD-001', 'process_name': '冲压'},
                    'OP001'
                )

        assert result['success'] is False
        assert 'Connection lost' in result['message']
        conn.rollback.assert_called_once()

    def test_publish_no_existing_row(self, mock_conn):
        """When rowcount is 0 and fetchone returns None (no existing task)."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        cursor.rowcount = 0
        cursor.fetchone.return_value = None  # no existing task

        with patch('services.wechat_report_service.get_connection', return_value=conn):
            with patch.object(WeChatReportService, '_ensure_tables'):
                result = WeChatReportService.publish_task_to_operator(
                    {'order_no': 'ORD-002', 'process_name': '焊接'},
                    'OP002'
                )

        assert result['success'] is True
        assert result['task_id'] == 0


# ===================================================================
#  _start_queue_processor / _queue_processor_started guard
# ===================================================================

class TestQueueProcessorLifecycle:
    """Cover _start_queue_processor and its idempotency guard."""

    def test_start_queue_processor(self):
        """_start_queue_processor starts a daemon thread."""
        from services.wechat_report_service import WeChatReportService

        with patch('threading.Thread') as mock_thread:
            mock_thread_instance = MagicMock()
            mock_thread.return_value = mock_thread_instance

            WeChatReportService._start_queue_processor()

            mock_thread.assert_called_once_with(
                target=WeChatReportService._process_queue,
                daemon=True,
                name="wechat-queue-processor"
            )
            mock_thread_instance.start.assert_called_once()
            assert WeChatReportService._queue_processor_started is True

    def test_start_queue_processor_idempotent(self):
        """Second call to _start_queue_processor does nothing."""
        from services.wechat_report_service import WeChatReportService
        WeChatReportService._queue_processor_started = True

        with patch('threading.Thread') as mock_thread:
            WeChatReportService._start_queue_processor()
            mock_thread.assert_not_called()


# ===================================================================
#  _process_queue — background polling loop
# ===================================================================

class TestProcessQueue:
    """Cover _process_queue — the background polling loop."""

    def test_process_queue_with_tasks(self, mock_conn):
        """_process_queue fetches and sends pending tasks."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn

        # Simulate 2 pending tasks + then break loop with exception
        cursor.fetchall.side_effect = [
            [
                {'id': 1, 'task_data': '{"order_no":"O1","process_name":"P1"}',
                 'operator_id': 'OP1', 'retry_count': 0},
                {'id': 2, 'task_data': '{"order_no":"O2","process_name":"P2"}',
                 'operator_id': 'OP2', 'retry_count': 1},
            ],
            # Second loop iteration -> fetchall raises to break the infinite loop
        ]

        with patch('services.wechat_report_service.get_connection', return_value=conn):
            with patch.object(WeChatReportService, '_send_task') as mock_send:
                with patch.object(WeChatReportService, '_ensure_tables'):
                    # _send_task will be called, then time.sleep(3) will be interrupted
                    # by raising in the second iteration
                    with patch('services.wechat_report_service.time.sleep',
                               side_effect=[None, KeyboardInterrupt]):
                        try:
                            WeChatReportService._process_queue()
                        except KeyboardInterrupt:
                            pass

        # Verify 2 tasks were sent via _send_task
        assert mock_send.call_count == 2
        mock_send.assert_any_call(conn, 1, {"order_no": "O1", "process_name": "P1"}, "OP1")
        mock_send.assert_any_call(conn, 2, {"order_no": "O2", "process_name": "P2"}, "OP2")

    def test_process_queue_exception_handling(self, mock_conn):
        """_process_queue catches exceptions in the outer try/except."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn

        cursor.execute.side_effect = Exception("Query failed")

        with patch('services.wechat_report_service.get_connection', return_value=conn):
            with patch('services.wechat_report_service.time.sleep',
                       side_effect=[KeyboardInterrupt]):
                with patch('services.wechat_report_service.logger.error') as mock_err:
                    try:
                        WeChatReportService._process_queue()
                    except KeyboardInterrupt:
                        pass

        # Should not raise; exception is caught and logged
        mock_err.assert_called()
        assert any('队列处理异常' in str(c) for c in mock_err.call_args_list)

    def test_process_queue_ensure_tables_call(self, mock_conn):
        """Each loop iteration calls _ensure_tables."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        cursor.fetchall.return_value = []

        with patch('services.wechat_report_service.get_connection', return_value=conn):
            with patch.object(WeChatReportService, '_ensure_tables') as mock_ensure:
                with patch('services.wechat_report_service.time.sleep',
                           side_effect=[KeyboardInterrupt]):
                    try:
                        WeChatReportService._process_queue()
                    except KeyboardInterrupt:
                        pass

        mock_ensure.assert_called_once()


# ===================================================================
#  _send_task — send individual task to container center
# ===================================================================

class TestSendTask:
    """Cover _send_task — HTTP send + status update logic."""

    def test_send_success(self, mock_conn):
        """Successful send: status -> 'success'."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        resp_mock = MagicMock()
        resp_mock.json.return_value = {'code': 0}
        mock_get_container = MagicMock(return_value='http://container:5002')

        with patch('services.wechat_report_service.requests.post',
                   return_value=resp_mock) as mock_post:
            with patch.object(WeChatReportService, '_get_container_url',
                              mock_get_container):
                WeChatReportService._send_task(
                    conn, 1, {'order_no': 'O1', 'process_name': 'P1'}, 'OP1'
                )

        # Should have set status='sending' first, then status='success'
        sending_call = call(
            "UPDATE wechat_tasks SET status = 'sending', updated_at = NOW() WHERE id = %s",
            (1,)
        )
        success_call = call(
            "UPDATE wechat_tasks SET status = 'success', updated_at = NOW() WHERE id = %s",
            (1,)
        )
        assert sending_call in cursor.execute.call_args_list
        assert success_call in cursor.execute.call_args_list
        mock_post.assert_called_once_with(
            "http://container:5002/api/wechat/dispatch",
            json={
                'type': 'wechat_task',
                'operator_id': 'OP1',
                'task_data': {'order_no': 'O1', 'process_name': 'P1'},
                'timestamp': ANY,
            },
            timeout=10
        )

    def test_send_failure_non_zero_code(self, mock_conn):
        """Container returns non-zero code: task retried."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        resp_mock = MagicMock()
        resp_mock.json.return_value = {'code': 1, 'message': 'Internal error'}
        # row for retry_count fetch
        cursor.fetchone.return_value = {'retry_count': 0}

        with patch('services.wechat_report_service.requests.post',
                   return_value=resp_mock):
            with patch.object(WeChatReportService, '_get_container_url',
                              return_value='http://container:5002'):
                WeChatReportService._send_task(
                    conn, 1, {'order_no': 'O1'}, 'OP1'
                )

        # Should have tried to update status to pending (retry) with incremented count
        update_calls = [
            c for c in cursor.execute.call_args_list
            if 'SET status' in str(c) and 'retry_count' in str(c)
        ]
        assert len(update_calls) == 1
        # retry_count should be 0+1=1
        assert '1' in str(update_calls[0]) or 1 in update_calls[0][0]

    def test_send_max_retries_dead_letter(self, mock_conn):
        """When retry_count >= MAX_RETRIES, status becomes 'dead_letter'."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        resp_mock = MagicMock()
        resp_mock.json.return_value = {'code': 1, 'message': 'Failed'}
        # Simulate that the task already has 3 retries (0-indexed, so fetch returns 3)
        cursor.fetchone.return_value = {'retry_count': 2}  # 2 + 1 = 3 = MAX_RETRIES

        with patch('services.wechat_report_service.requests.post',
                   return_value=resp_mock):
            with patch.object(WeChatReportService, '_get_container_url',
                              return_value='http://container:5002'):
                WeChatReportService._send_task(
                    conn, 1, {'order_no': 'O1'}, 'OP1'
                )

        # Should have dead_letter in the status update
        dead_letter_calls = [
            c for c in cursor.execute.call_args_list
            if 'dead_letter' in str(c)
        ]
        assert len(dead_letter_calls) >= 1
        # conn.commit should have been called in finally
        assert conn.commit.call_count >= 1


# ===================================================================
#  process_callback
# ===================================================================

class TestProcessCallback:
    """Cover process_callback — handling WeChat work report callbacks."""

    def test_callback_missing_fields(self):
        """Missing order_no or process_name returns error."""
        from services.wechat_report_service import WeChatReportService
        result = WeChatReportService.process_callback({'order_no': '', 'process_name': ''})
        assert result['success'] is False
        assert '缺少 order_no 或 process_name' in result['message']

    def test_callback_record_not_found(self, mock_conn):
        """No matching process record returns error."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        cursor.fetchone.return_value = None  # no process record found

        with patch('services.wechat_report_service.get_connection', return_value=conn):
            result = WeChatReportService.process_callback({
                'order_no': 'ORD-001', 'process_name': '冲压',
                'operator_id': 'OP1', 'completed_qty': 100,
                'qualified_qty': 98, 'work_hours': 4.5, 'status': '进行中',
            })

        assert result['success'] is False
        assert '未找到工序记录' in result['message']

    def test_callback_progress_report(self, mock_conn):
        """Progress report (待开始 -> 进行中) triggers START report type."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        cursor.fetchone.side_effect = [
            _make_record(id=1, status='待开始', prod_id=10, order_id=100),
            None,  # next_proc: no next process
        ]

        with patch('services.wechat_report_service.get_connection', return_value=conn):
            result = WeChatReportService.process_callback({
                'order_no': 'ORD-001', 'process_name': '冲压',
                'operator_id': 'OP1', 'completed_qty': 50,
                'qualified_qty': 50, 'work_hours': 2, 'status': '进行中',
            })

        assert result['success'] is True
        # Check that start_time was appended
        update_sql_calls = [str(c) for c in cursor.execute.call_args_list]
        assert any('start_time = NOW()' in s for s in update_sql_calls)
        assert any('INSERT INTO workreport_records' in s for s in update_sql_calls)
        assert any('report_type' in s for s in update_sql_calls)

    def test_callback_complete_no_next_process(self, mock_conn):
        """Completion of last process updates production order and order status."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        cursor.fetchone.side_effect = [
            _make_record(id=1, status='进行中', prod_id=10, order_id=100, process_seq=3),
            None,  # next_proc: no next process (this is the last one)
        ]

        with patch('services.wechat_report_service.get_connection', return_value=conn):
            result = WeChatReportService.process_callback({
                'order_no': 'ORD-001', 'process_name': '冲压',
                'operator_id': 'OP1', 'completed_qty': 100,
                'qualified_qty': 100, 'work_hours': 5, 'status': '已完成',
            })

        assert result['success'] is True
        update_calls = [str(c) for c in cursor.execute.call_args_list]
        # Should update production_orders to '已完成'
        assert any('已完成' in s and 'production_orders' in s for s in update_calls)
        # Should update orders to '质检中'
        assert any('质检中' in s and 'orders' in s for s in update_calls)

    def test_callback_complete_with_next_process(self, mock_conn):
        """Completion with a next process updates production to '生产中'."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        cursor.fetchone.side_effect = [
            _make_record(id=1, status='进行中', prod_id=10, order_id=100, process_seq=2),
            {'id': 2, 'process_name': '焊接', 'process_seq': 3, 'status': '待开始'},
        ]

        with patch('services.wechat_report_service.get_connection', return_value=conn):
            result = WeChatReportService.process_callback({
                'order_no': 'ORD-001', 'process_name': '冲压',
                'operator_id': 'OP1', 'completed_qty': 100,
                'qualified_qty': 100, 'work_hours': 5, 'status': '已完成',
            })

        assert result['success'] is True
        update_calls = [str(c) for c in cursor.execute.call_args_list]
        # Should NOT update production to '已完成' (since next process exists)
        assert not any('已完成' in s and 'production_orders' in s for s in update_calls)
        # Should still set production to '生产中'
        assert any('生产中' in s and 'production_orders' in s for s in update_calls)

    def test_callback_exception_rollback(self, mock_conn):
        """DB exception during callback triggers rollback."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        cursor.execute.side_effect = Exception("Query error")

        with patch('services.wechat_report_service.get_connection', return_value=conn):
            result = WeChatReportService.process_callback({
                'order_no': 'ORD-001', 'process_name': '冲压',
                'operator_id': 'OP1', 'completed_qty': 100,
                'qualified_qty': 98, 'work_hours': 4.5, 'status': '进行中',
            })

        assert result['success'] is False
        conn.rollback.assert_called_once()

    def test_callback_update_wechat_tasks_result(self, mock_conn):
        """Callback updates wechat_tasks result_data."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        cursor.fetchone.side_effect = [
            _make_record(id=1, status='待开始', prod_id=10, order_id=100),
            None,
        ]

        callback_data = {
            'order_no': 'ORD-001', 'process_name': '冲压',
            'operator_id': 'OP1', 'completed_qty': 100,
            'qualified_qty': 98, 'work_hours': 5, 'status': '已完成',
            'remark': 'good',
        }

        with patch('services.wechat_report_service.get_connection', return_value=conn):
            result = WeChatReportService.process_callback(callback_data)

        assert result['success'] is True
        update_calls = [str(c) for c in cursor.execute.call_args_list]
        assert any('result_data' in s and 'wechat_tasks' in s for s in update_calls)


# ===================================================================
#  sync_report_status
# ===================================================================

class TestSyncReportStatus:
    """Cover sync_report_status — query report status for an order."""

    def test_sync_success(self, mock_conn):
        """Successful query returns structured data."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        cursor.fetchall.return_value = [
            _make_record(id=1, process_name='冲压', process_seq=1,
                         completed_qty=50, status='进行中'),
            _make_record(id=2, process_name='焊接', process_seq=2,
                         completed_qty=100, status='已完成'),
        ]

        with patch('services.wechat_report_service.get_connection', return_value=conn):
            result = WeChatReportService.sync_report_status('ORD-001')

        assert result['success'] is True
        assert len(result['data']) == 2
        assert result['data'][0]['process_name'] == '冲压'
        assert result['data'][1]['process_name'] == '焊接'

    def test_sync_exception(self, mock_conn):
        """DB exception returns failure with empty data."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        cursor.execute.side_effect = Exception("DB error")

        with patch('services.wechat_report_service.get_connection', return_value=conn):
            result = WeChatReportService.sync_report_status('ORD-001')

        assert result['success'] is False
        assert result['data'] == []

    def test_sync_success_empty_records(self, mock_conn):
        """No records found returns empty data list."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        cursor.fetchall.return_value = []

        with patch('services.wechat_report_service.get_connection', return_value=conn):
            result = WeChatReportService.sync_report_status('ORD-001')

        assert result['success'] is True
        assert result['data'] == []


# ===================================================================
#  batch_update_status
# ===================================================================

class TestBatchUpdateStatus:
    """Cover batch_update_status — batch processing of callback items."""

    def test_batch_invalid_input(self):
        """Non-list input returns error."""
        from services.wechat_report_service import WeChatReportService
        result = WeChatReportService.batch_update_status("not_a_list")
        assert result['success'] is False
        assert result['updated'] == 0

    def test_batch_all_success(self, mock_conn):
        """All items succeed."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        cursor.fetchone.side_effect = [
            _make_record(id=1, order_id=100, prod_id=10),
            None,
            _make_record(id=2, order_id=100, prod_id=10),
            None,
        ]

        items = [
            {'order_no': 'O1', 'process_name': 'P1', 'status': '已完成',
             'completed_qty': 100, 'qualified_qty': 100, 'work_hours': 5},
            {'order_no': 'O2', 'process_name': 'P2', 'status': '已完成',
             'completed_qty': 50, 'qualified_qty': 50, 'work_hours': 3},
        ]

        with patch('services.wechat_report_service.get_connection', return_value=conn):
            result = WeChatReportService.batch_update_status(items)

        assert result['success'] is True
        assert result['updated'] == 2
        assert result['failed'] == 0

    def test_batch_some_failed(self):
        """When process_callback returns failure, failed count increments."""
        from services.wechat_report_service import WeChatReportService

        with patch.object(WeChatReportService, 'process_callback',
                          side_effect=[
                              {'success': True, 'message': 'ok'},
                              {'success': False, 'message': 'not found'},
                          ]):
            items = [
                {'order_no': 'O1', 'process_name': 'P1'},
                {'order_no': 'O2', 'process_name': 'P2'},
            ]
            result = WeChatReportService.batch_update_status(items)

        assert result['success'] is True
        assert result['updated'] == 1
        assert result['failed'] == 1

    def test_batch_exception_in_item(self, mock_conn):
        """When process_callback raises, failed count increments."""
        from services.wechat_report_service import WeChatReportService

        with patch.object(WeChatReportService, 'process_callback',
                          side_effect=[Exception("Boom"), {'success': True}]):
            items = [
                {'order_no': 'O1', 'process_name': 'P1'},
                {'order_no': 'O2', 'process_name': 'P2'},
            ]
            result = WeChatReportService.batch_update_status(items)

        assert result['success'] is True
        assert result['updated'] == 1
        assert result['failed'] == 1


# ===================================================================
#  update_operator
# ===================================================================

class TestUpdateOperator:
    """Cover update_operator — updating operator on process records."""

    def test_update_success(self, mock_conn):
        """Successful update returns success."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        cursor.rowcount = 1

        with patch('services.wechat_report_service.get_connection', return_value=conn):
            result = WeChatReportService.update_operator('ORD-001', '冲压', 'OP001')

        assert result['success'] is True
        assert '操作员更新成功' in result['message']

    def test_update_not_found(self, mock_conn):
        """No matching record returns not found."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        cursor.rowcount = 0

        with patch('services.wechat_report_service.get_connection', return_value=conn):
            result = WeChatReportService.update_operator('ORD-001', '冲压', 'OP001')

        assert result['success'] is False
        assert '未找到匹配的工序记录' in result['message']

    def test_update_exception(self, mock_conn):
        """DB exception returns error."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        cursor.execute.side_effect = Exception("DB error")

        with patch('services.wechat_report_service.get_connection', return_value=conn):
            result = WeChatReportService.update_operator('ORD-001', '冲压', 'OP001')

        assert result['success'] is False
        assert '更新操作员失败' in result['message']
        conn.rollback.assert_called_once()


# ===================================================================
#  get_dead_tasks
# ===================================================================

class TestGetDeadTasks:
    """Cover get_dead_tasks — retrieving dead letter tasks."""

    def test_get_dead_tasks_with_results(self, mock_conn):
        """Returns list of dead letter tasks."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        # Use real dicts to avoid dict(MagicMock) issues
        cursor.fetchall.return_value = [
            {'id': 1, 'order_no': 'ORD-001', 'process_name': '冲压',
             'task_data': '{"qty":50}', 'retry_count': 3,
             'last_error': 'Timeout', 'last_retry_at': None,
             'created_at': None, 'updated_at': None},
        ]

        with patch('services.wechat_report_service.get_connection', return_value=conn):
            result = WeChatReportService.get_dead_tasks()

        assert len(result) == 1
        assert result[0]['order_no'] == 'ORD-001'

    def test_get_dead_tasks_empty(self, mock_conn):
        """Returns empty list when no dead tasks."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        cursor.fetchall.return_value = []

        with patch('services.wechat_report_service.get_connection', return_value=conn):
            result = WeChatReportService.get_dead_tasks()

        assert result == []

    def test_get_dead_tasks_warning_log(self, mock_conn):
        """When 10+ dead tasks, warning log is written."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        rows = [
            MagicMock(**{'__getitem__.side_effect': lambda k, _i=i: {
                'id': _i, 'order_no': f'ORD-{_i}', 'process_name': 'P1',
                'task_data': '{}', 'retry_count': 3,
                'last_error': 'Err', 'last_retry_at': None,
                'created_at': None, 'updated_at': None,
            }[k]})
            for i in range(12)
        ]
        cursor.fetchall.return_value = rows

        with patch('services.wechat_report_service.get_connection', return_value=conn):
            with patch('services.wechat_report_service.logger.warning') as mock_warn:
                result = WeChatReportService.get_dead_tasks()

        assert len(result) == 12
        mock_warn.assert_called_once()


# ===================================================================
#  retry_dead_task — comprehensive coverage
# ===================================================================

class TestRetryDeadTask:
    """Cover retry_dead_task — atomic retry of dead letter tasks."""

    def test_retry_atomic_skip(self, mock_conn):
        """When another process already claimed the task, return skipped."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        cursor.rowcount = 0  # UPDATE affected 0 rows (already claimed)

        with patch('services.wechat_report_service.get_connection', return_value=conn):
            result = WeChatReportService.retry_dead_task(1)

        assert result['success'] is True
        assert result['skipped'] is True
        assert '已被其他进程处理' in result['message']

    def test_retry_missing_task_data(self, mock_conn):
        """When task_data is missing or empty, return error."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        cursor.rowcount = 1  # successfully claimed
        cursor.fetchone.return_value = {'task_data': None, 'operator_id': 'OP1'}

        with patch('services.wechat_report_service.get_connection', return_value=conn):
            result = WeChatReportService.retry_dead_task(1)

        assert result['success'] is False
        assert '任务数据缺失' in result['message']

    def test_retry_invalid_json(self, mock_conn):
        """When task_data is invalid JSON, return error."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        cursor.rowcount = 1
        cursor.fetchone.return_value = {'task_data': 'not valid json', 'operator_id': 'OP1'}

        with patch('services.wechat_report_service.get_connection', return_value=conn):
            result = WeChatReportService.retry_dead_task(1)

        assert result['success'] is False
        assert 'JSON解析失败' in result['message']

    def test_retry_connection_error(self, mock_conn):
        """When container center is unreachable, keep in dead_letter."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        cursor.rowcount = 1
        cursor.fetchone.return_value = {
            'task_data': '{"order_no":"O1","process_name":"P1"}',
            'operator_id': 'OP1',
        }

        # We need 2 connections: the first one for claiming, the second for rollback handling
        conn2 = MagicMock()
        cursor2 = MagicMock()
        conn2.cursor.return_value = cursor2
        mock_get_conn = MagicMock(side_effect=[conn, conn2])

        with patch('services.wechat_report_service.get_connection', mock_get_conn):
            with patch('services.wechat_report_service.requests.post',
                       side_effect=requests.ConnectionError("Connection refused")):
                result = WeChatReportService.retry_dead_task(1)

        assert result['success'] is False
        assert '容器中心连接失败' in result['message']
        # The second connection should have rolled back to dead_letter
        cursor2.execute.assert_called()
        calls_str = str(cursor2.execute.call_args_list)
        assert 'dead_letter' in calls_str or "dead_letter" in calls_str
        conn2.commit.assert_called_once()

    def test_retry_send_exception(self, mock_conn):
        """When requests.post raises a non-ConnectionError exception."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        cursor.rowcount = 1
        cursor.fetchone.return_value = {
            'task_data': '{"order_no":"O1"}',
            'operator_id': 'OP1',
        }

        conn2 = MagicMock()
        cursor2 = MagicMock()
        conn2.cursor.return_value = cursor2
        mock_get_conn = MagicMock(side_effect=[conn, conn2])

        with patch('services.wechat_report_service.get_connection', mock_get_conn):
            with patch('services.wechat_report_service.requests.post',
                       side_effect=Exception("Timeout")):
                result = WeChatReportService.retry_dead_task(1)

        assert result['success'] is False
        assert '发送异常' in result['message']
        conn2.commit.assert_called_once()

    def test_retry_success(self, mock_conn):
        """Successful retry — code==0 from container center."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        cursor.rowcount = 1
        cursor.fetchone.return_value = {
            'task_data': '{"order_no":"O1","process_name":"P1"}',
            'operator_id': 'OP1',
        }

        resp_mock = MagicMock()
        resp_mock.json.return_value = {'code': 0, 'data': {'ack_id': 'ACK-123'}}

        conn2 = MagicMock()
        cursor2 = MagicMock()
        conn2.cursor.return_value = cursor2
        mock_get_conn = MagicMock(side_effect=[conn, conn2])

        with patch('services.wechat_report_service.get_connection', mock_get_conn):
            with patch.object(WeChatReportService, '_get_container_url',
                              return_value='http://container:5002'):
                with patch('services.wechat_report_service.requests.post',
                           return_value=resp_mock):
                    result = WeChatReportService.retry_dead_task(1)

        assert result['success'] is True
        assert '已成功发送' in result['message']
        # Verify second connection updated status to 'success'
        update_calls = [str(c) for c in cursor2.execute.call_args_list]
        assert any("'success'" in s for s in update_calls)
        conn2.commit.assert_called_once()

    def test_retry_container_returns_failure(self, mock_conn):
        """When container returns non-zero code, keep in dead_letter."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        cursor.rowcount = 1
        cursor.fetchone.return_value = {
            'task_data': '{"order_no":"O1"}',
            'operator_id': 'OP1',
        }

        resp_mock = MagicMock()
        resp_mock.json.return_value = {'code': 1, 'message': 'Internal error'}

        conn2 = MagicMock()
        cursor2 = MagicMock()
        conn2.cursor.return_value = cursor2
        mock_get_conn = MagicMock(side_effect=[conn, conn2])

        with patch('services.wechat_report_service.get_connection', mock_get_conn):
            with patch('services.wechat_report_service.requests.post',
                       return_value=resp_mock):
                result = WeChatReportService.retry_dead_task(1)

        assert result['success'] is False
        assert '容器中心返回' in result['message']
        conn2.commit.assert_called_once()

    def test_retry_outer_exception(self, mock_conn):
        """When an outer exception occurs, catch and return error."""
        from services.wechat_report_service import WeChatReportService
        conn, cursor = mock_conn
        cursor.execute.side_effect = Exception("Unexpected error")

        with patch('services.wechat_report_service.get_connection', return_value=conn):
            result = WeChatReportService.retry_dead_task(1)

        assert result['success'] is False
        assert '重发异常' in result['message']
        conn.close.assert_called_once()


