"""AlertEngine 单元测试"""
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from container_center.services.alert_engine import AlertEngine


def _make_mock_store():
    """创建 Mock 存储对象"""
    doc_store = MagicMock()
    doc_store.get_packages.return_value = []
    doc_store.update_status = MagicMock()
    doc_store.update = MagicMock()

    alert_store = MagicMock()
    alert_store.query.return_value = {'data': []}
    alert_store.create = MagicMock()

    config_store = MagicMock()
    config_store.get.return_value = {}

    return doc_store, alert_store, config_store


class TestAlertEngineInit(unittest.TestCase):
    """AlertEngine 初始化测试"""

    def test_init_sets_attributes(self):
        doc, alt, cfg = _make_mock_store()
        engine = AlertEngine(doc, alt, cfg, send_message=MagicMock(), get_operators=MagicMock())
        self.assertIs(engine.doc_store, doc)
        self.assertIs(engine.alert_store, alt)
        self.assertIs(engine.config_store, cfg)
        self.assertIsNone(engine._thread)
        self.assertIsNotNone(engine._stop_event)


class TestFlatten(unittest.TestCase):
    """静态方法 _flatten 测试"""

    def test_flatten_with_doc_data(self):
        pkg = {'id': '1', 'title': 'test', 'doc_data': {'status': 'done', 'price': 100}}
        flat = AlertEngine._flatten(pkg)
        self.assertEqual(flat['id'], '1')
        self.assertEqual(flat['title'], 'test')
        self.assertEqual(flat['status'], 'done')
        self.assertEqual(flat['price'], 100)

    def test_flatten_without_doc_data(self):
        pkg = {'id': '1', 'title': 'test', 'status': 'pending'}
        flat = AlertEngine._flatten(pkg)
        self.assertEqual(flat['id'], '1')
        self.assertEqual(flat['title'], 'test')
        self.assertEqual(flat['status'], 'pending')

    def test_flatten_empty(self):
        flat = AlertEngine._flatten({})
        self.assertEqual(flat, {})

    def test_flatten_preserves_original_keys(self):
        pkg = {'id': '1', 'doc_data': {'status': 'done'}, 'extra': 'val'}
        flat = AlertEngine._flatten(pkg)
        self.assertEqual(flat['extra'], 'val')
        self.assertEqual(flat['status'], 'done')


class TestIsDuplicate(unittest.TestCase):
    """_is_duplicate 去重检测测试"""

    def setUp(self):
        doc, alt, cfg = _make_mock_store()
        self.engine = AlertEngine(doc, alt, cfg, send_message=MagicMock(), get_operators=MagicMock())

    def test_no_alerts(self):
        self.engine.alert_store.query.return_value = {'data': []}
        result = self.engine._is_duplicate('doc1', 'task_overdue')
        self.assertFalse(result)

    def test_recent_duplicate_found(self):
        now = datetime.now()
        self.engine.alert_store.query.return_value = {
            'data': [
                {'doc_id': 'doc1', 'alert_type': 'task_overdue', 'created_at': now.isoformat()}
            ]
        }
        result = self.engine._is_duplicate('doc1', 'task_overdue')
        self.assertTrue(result)

    def test_different_doc_id_not_duplicate(self):
        now = datetime.now()
        self.engine.alert_store.query.return_value = {
            'data': [
                {'doc_id': 'other_doc', 'alert_type': 'task_overdue', 'created_at': now.isoformat()}
            ]
        }
        result = self.engine._is_duplicate('doc1', 'task_overdue')
        self.assertFalse(result)

    def test_old_alert_not_duplicate(self):
        old = datetime.now() - timedelta(hours=2)
        self.engine.alert_store.query.return_value = {
            'data': [
                {'doc_id': 'doc1', 'alert_type': 'task_overdue', 'created_at': old.isoformat()}
            ]
        }
        result = self.engine._is_duplicate('doc1', 'task_overdue', minutes=30)
        self.assertFalse(result)

    def test_invalid_date_not_crash(self):
        self.engine.alert_store.query.return_value = {
            'data': [
                {'doc_id': 'doc1', 'alert_type': 'task_overdue', 'created_at': 'invalid-date'}
            ]
        }
        result = self.engine._is_duplicate('doc1', 'task_overdue')
        self.assertFalse(result)


class TestCheckOverdueTasks(unittest.TestCase):
    """check_overdue_tasks 超时任务检测测试"""

    def setUp(self):
        doc, alt, cfg = _make_mock_store()
        self.send_msg = MagicMock()
        self.get_ops = MagicMock()
        self.get_ops.return_value = {'op1': {'name': '张三'}}
        self.engine = AlertEngine(doc, alt, cfg, send_message=self.send_msg, get_operators=self.get_ops)

    def test_no_packages_no_error(self):
        self.engine.doc_store.get_packages.return_value = []
        self.engine.check_overdue_tasks()
        self.send_msg.assert_not_called()

    def test_pending_task_not_overdue_skipped(self):
        now = datetime.now()
        self.engine.config_store.get.return_value = {'auto_reassign_timeout': 120}
        self.engine.doc_store.get_packages.return_value = [
            {'id': 'p1', 'doc_data': {'status': 'pending', 'created_at': now.isoformat(), 'title': 'test'}}
        ]
        self.engine.check_overdue_tasks()
        self.send_msg.assert_not_called()
        self.engine.doc_store.update_status.assert_not_called()

    def test_pending_task_overdue_triggers_alert(self):
        old = datetime.now() - timedelta(hours=3)
        self.engine.config_store.get.return_value = {'auto_reassign_timeout': 120}
        self.engine.doc_store.get_packages.return_value = [
            {
                'id': 'p1',
                'doc_data': {
                    'status': 'pending',
                    'created_at': old.isoformat(),
                    'title': '超时任务',
                    'related_order': 'WO001',
                    'target_operator': 'op1'
                }
            }
        ]
        self.engine.check_overdue_tasks()

        # Should update status to overdue
        self.engine.doc_store.update_status.assert_called_with('p1', 'overdue', 'work_order')

        # Should create alert
        self.engine.alert_store.create.assert_called_once()

        # Should send message
        self.send_msg.assert_called_once()
        args, kwargs = self.send_msg.call_args
        self.assertIn('超时任务', args[0])
        self.assertIn('WO001', args[0])
        self.assertEqual(kwargs.get('msg_type'), 'markdown')

    def test_overdue_duplicate_alert_not_created(self):
        old = datetime.now() - timedelta(hours=3)
        self.engine.config_store.get.return_value = {'auto_reassign_timeout': 120}
        self.engine.doc_store.get_packages.return_value = [
            {'id': 'p1', 'doc_data': {'status': 'pending', 'created_at': old.isoformat(), 'title': 'test'}}
        ]
        # Already has alert
        self.engine.alert_store.query.return_value = {
            'data': [
                {'doc_id': 'p1', 'alert_type': 'task_overdue', 'created_at': datetime.now().isoformat()}
            ]
        }
        self.engine.check_overdue_tasks()
        # Should set the status but not create redundant alert
        self.engine.doc_store.update_status.assert_called_once()
        self.engine.alert_store.create.assert_not_called()


class TestCheckOutsourceReminders(unittest.TestCase):
    """check_outsource_reminders 委外超期提醒测试"""

    def setUp(self):
        doc, alt, cfg = _make_mock_store()
        self.send_msg = MagicMock()
        self.get_ops = MagicMock()
        self.get_ops.return_value = {'op1': {'name': '李四'}}
        self.engine = AlertEngine(doc, alt, cfg, send_message=self.send_msg, get_operators=self.get_ops)

    def test_disabled_config_returns_early(self):
        self.engine.config_store.get.return_value = {'enabled': False}
        self.engine.check_outsource_reminders()
        self.send_msg.assert_not_called()

    def test_no_outsource_packages_no_error(self):
        self.engine.config_store.get.return_value = {'enabled': True, 'overdue_remind_times': ['09:00']}
        self.engine.doc_store.get_packages.return_value = []
        self.engine.check_outsource_reminders()
        self.send_msg.assert_not_called()

    def test_completed_outsource_skipped(self):
        now = datetime.now()
        self.engine.config_store.get.return_value = {
            'enabled': True,
            'overdue_remind_times': [now.strftime('%H:%M')],
            'remind_days': [3]
        }
        self.engine.doc_store.get_packages.return_value = [
            {
                'id': 'p1',
                'data_type': 'outsource',
                'status': 'completed',
                'promised_date': (now - timedelta(days=1)).isoformat()
            }
        ]
        self.engine.check_outsource_reminders()
        self.send_msg.assert_not_called()

    def test_overdue_outsource_triggers_alert(self):
        now = datetime.now()
        overdue = now - timedelta(days=2)
        self.engine.config_store.get.return_value = {
            'enabled': True,
            'overdue_remind_times': [now.strftime('%H:%M')],
            'remind_days': [3]
        }
        self.engine.doc_store.get_packages.return_value = [
            {
                'id': 'p1',
                'data_type': 'outsource',
                'status': 'dispatched',
                'title': '外协加工',
                'target_operator': 'op1',
                'promised_date': overdue.isoformat()
            }
        ]
        self.engine.check_outsource_reminders()

        self.send_msg.assert_called_once()
        args = self.send_msg.call_args[0][0]
        self.assertIn('外协逾期催单', args)
        self.assertIn('外协加工', args)
        self.assertIn('李四', args)

    def test_due_soon_reminder_triggers(self):
        now = datetime.now()
        due_soon = now + timedelta(days=3, hours=6)
        self.engine.config_store.get.return_value = {
            'enabled': True,
            'overdue_remind_times': ['09:00'],
            'remind_days': [3]
        }
        self.engine.doc_store.get_packages.return_value = [
            {
                'id': 'p1',
                'data_type': 'outsource',
                'status': 'dispatched',
                'title': '外协加工',
                'target_operator': 'op1',
                'promised_date': due_soon.isoformat()
            }
        ]
        self.engine.check_outsource_reminders()

        self.send_msg.assert_called_once()
        args = self.send_msg.call_args[0][0]
        self.assertIn('外协到期提醒', args)

    def test_reminder_already_sent_skipped(self):
        now = datetime.now()
        due_soon = now + timedelta(days=3)
        self.engine.config_store.get.return_value = {
            'enabled': True,
            'overdue_remind_times': ['09:00'],
            'remind_days': [3]
        }
        self.engine.doc_store.get_packages.return_value = [
            {
                'id': 'p1',
                'data_type': 'outsource',
                'status': 'dispatched',
                'title': '外协加工',
                'target_operator': 'op1',
                'promised_date': due_soon.isoformat(),
                'reminder_sent': '3days'
            }
        ]
        self.engine.check_outsource_reminders()
        self.send_msg.assert_not_called()


class TestLifecycle(unittest.TestCase):
    """start/stop 生命周期测试"""

    def setUp(self):
        doc, alt, cfg = _make_mock_store()
        self.engine = AlertEngine(doc, alt, cfg, send_message=MagicMock(), get_operators=MagicMock())

    def test_start_creates_thread(self):
        self.engine.start(interval_seconds=99999)
        self.assertIsNotNone(self.engine._thread)
        self.assertTrue(self.engine._thread.is_alive())
        self.engine.stop()

    def test_stop_stops_thread(self):
        self.engine.start(interval_seconds=99999)
        self.engine.stop()
        self.assertTrue(self.engine._stop_event.is_set())

    def test_start_twice_no_duplicate_thread(self):
        self.engine.start(interval_seconds=99999)
        thread_id = id(self.engine._thread)
        self.engine.start(interval_seconds=99999)
        self.assertEqual(id(self.engine._thread), thread_id)
        self.engine.stop()


if __name__ == '__main__':
    unittest.main(verbosity=2)
