# Q1.1-Q1.3: EventStore 全路径测试
import pytest, sys, os, json
from unittest.mock import MagicMock, patch


from core.event_store import EventStore, set_connection_factory


class TestEventStore:
    """P0修复验证：连接可注入"""

    def teardown_method(self):
        set_connection_factory(None)

    def _mock_conn(self, fetchall_result=None):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = fetchall_result or []
        mock_conn.cursor.return_value = mock_cursor
        set_connection_factory(lambda: mock_conn)
        return mock_conn, mock_cursor

    # Q1.1: 写入
    def test_append_success(self):
        conn, cursor = self._mock_conn()
        ok = EventStore.append('order', 'ORD-001', 'order:created', {'status': 'draft'})
        assert ok is True
        cursor.execute.assert_called_once()

    def test_append_payload_too_large_rejected(self):
        self._mock_conn()
        big = {'data': 'x' * 11000}
        ok = EventStore.append('order', 'ORD-002', 'order:created', big)
        assert ok is False

    def test_append_db_error_returns_false(self):
        conn, cursor = self._mock_conn()
        cursor.execute.side_effect = Exception('DB down')
        ok = EventStore.append('order', 'ORD-003', 'order:created', {})
        assert ok is False

    # Q1.2: 查询
    def test_get_events_returns_chronological(self):
        events = [
            (1, 'order', 'ORD-001', 'order:created', '{"status":"draft"}', '2026-01-01 10:00:00'),
            (2, 'order', 'ORD-001', 'order:confirmed', '{"status":"confirmed"}', '2026-01-01 11:00:00'),
        ]
        self._mock_conn(fetchall_result=events)
        result = EventStore.get_events('order', 'ORD-001')
        assert len(result) == 2
        assert result[0]['type'] == 'order:created'
        assert result[1]['type'] == 'order:confirmed'

    def test_get_events_empty_aggregate(self):
        self._mock_conn(fetchall_result=[])
        result = EventStore.get_events('order', 'NONEXIST')
        assert result == []

    def test_get_events_db_error_returns_empty(self):
        conn, cursor = self._mock_conn()
        cursor.execute.side_effect = Exception('DB down')
        result = EventStore.get_events('order', 'ORD-001')
        assert result == []

    # Q1.3: 回放
    def test_replay_calls_handler_for_each_event(self):
        events = [
            (1, 'order', 'ORD-001', 'order:created', '{}', '2026-01-01'),
            (2, 'order', 'ORD-001', 'order:confirmed', '{}', '2026-01-02'),
        ]
        self._mock_conn(fetchall_result=events)
        called = []
        def handler(ev): called.append(ev['type'])
        count = EventStore.replay('order', 'ORD-001', handler)
        assert count == 2
        assert called == ['order:created', 'order:confirmed']

    def test_replay_handler_exception_does_not_stop(self):
        events = [
            (1, 'order', 'ORD-001', 'order:created', '{}', '2026-01-01'),
            (2, 'order', 'ORD-001', 'order:confirmed', '{}', '2026-01-02'),
        ]
        self._mock_conn(fetchall_result=events)
        called = []
        def handler(ev):
            called.append(ev['type'])
            if ev['type'] == 'order:created':
                raise RuntimeError('boom')
        count = EventStore.replay('order', 'ORD-001', handler)
        assert count == 1  # 第二条继续执行
        assert called == ['order:created', 'order:confirmed']
