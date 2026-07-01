# -*- coding: utf-8 -*-
"""
notifier 单元测试

覆盖：
- WeChatNotifier 初始化
- enabled 属性
- notify_new_task
- notify_task_assigned
- notify_task_completed
- notify_low_stock
- 通知禁用场景
- 异常处理
"""
import pytest
from unittest.mock import MagicMock, patch


class TestWeChatNotifierInit:
    """WeChatNotifier 初始化测试"""

    def test_init_default_enabled(self):
        with patch.dict('os.environ', {}, clear=True):
            from services.notifier import WeChatNotifier
            n = WeChatNotifier()
            assert n._enabled is True

    def test_init_disabled(self):
        with patch.dict('os.environ', {'ENABLE_WECHAT_NOTIFY': 'false'}):
            from services.notifier import WeChatNotifier
            n = WeChatNotifier()
            assert n._enabled is False

    def test_init_task_assigned_off(self):
        with patch.dict('os.environ', {'NOTIFY_ON_TASK_ASSIGNED': 'false'}):
            from services.notifier import WeChatNotifier
            n = WeChatNotifier()
            assert n._notify_task_assigned is False

    def test_init_low_stock_off(self):
        with patch.dict('os.environ', {'NOTIFY_ON_LOW_STOCK': 'true'}):
            from services.notifier import WeChatNotifier
            n = WeChatNotifier()
            assert n._notify_low_stock is True

    def test_initialize(self):
        from services.notifier import WeChatNotifier
        n = WeChatNotifier()
        hub = MagicMock()
        n.initialize(message_hub=hub, container_center=MagicMock())
        assert n._message_hub is hub


class TestWeChatNotifierEnabled:
    """enabled 属性测试"""

    def test_get_enabled(self):
        from services.notifier import WeChatNotifier
        n = WeChatNotifier()
        n._enabled = True
        assert n.enabled is True

    def test_set_enabled(self):
        from services.notifier import WeChatNotifier
        n = WeChatNotifier()
        n.enabled = False
        assert n._enabled is False


class TestNotifyNewTask:
    """notify_new_task 测试"""

    def setup_method(self):
        from services.notifier import WeChatNotifier
        self.n = WeChatNotifier()
        self.n.initialize(message_hub=MagicMock(), container_center=MagicMock())

    def test_disabled_returns_false(self):
        self.n._enabled = False
        result = self.n.notify_new_task({'order_no': 'ORD001'})
        assert result is False

    def test_no_hub_returns_false(self):
        self.n._message_hub = None
        result = self.n.notify_new_task({'order_no': 'ORD001'})
        assert result is False

    def test_success(self):
        self.n._message_hub.broadcast.return_value = True
        result = self.n.notify_new_task({
            'task_id': 'T001',
            'order_no': 'ORD001',
            'process': '焊接',
            'planned_qty': 100
        })
        assert result is True
        assert self.n._message_hub.broadcast.called

    def test_with_operator(self):
        self.n._message_hub.broadcast.return_value = True
        result = self.n.notify_new_task({
            'task_id': 'T001',
            'order_no': 'ORD001',
            'process': '焊接',
            'operator_id': 'OP001'
        })
        assert result is True
        args = self.n._message_hub.broadcast.call_args[0][0]
        assert 'OP001' in args

    def test_broadcast_returns_false(self):
        self.n._message_hub.broadcast.return_value = False
        result = self.n.notify_new_task({'order_no': 'ORD001'})
        assert result is False

    def test_broadcast_raises(self):
        self.n._message_hub.broadcast.side_effect = Exception('error')
        result = self.n.notify_new_task({'order_no': 'ORD001'})
        assert result is False


class TestNotifyTaskAssigned:
    """notify_task_assigned 测试"""

    def setup_method(self):
        from services.notifier import WeChatNotifier
        self.n = WeChatNotifier()
        self.n.initialize(message_hub=MagicMock(), container_center=MagicMock())

    def test_disabled(self):
        self.n._enabled = False
        assert self.n.notify_task_assigned({}, 'OP001') is False

    def test_setting_off(self):
        self.n._notify_task_assigned = False
        assert self.n.notify_task_assigned({}, 'OP001') is False

    def test_no_hub(self):
        self.n._message_hub = None
        assert self.n.notify_task_assigned({}, 'OP001') is False

    def test_success(self):
        self.n._message_hub.send_to_user.return_value = True
        result = self.n.notify_task_assigned({
            'order_no': 'ORD001', 'process': '焊接', 'planned_qty': 50
        }, 'OP001')
        assert result is True

    def test_failure(self):
        self.n._message_hub.send_to_user.return_value = False
        assert self.n.notify_task_assigned({}, 'OP001') is False

    def test_exception(self):
        self.n._message_hub.send_to_user.side_effect = Exception('error')
        assert self.n.notify_task_assigned({}, 'OP001') is False


class TestNotifyLowStock:
    """notify_low_stock 测试"""

    def setup_method(self):
        from services.notifier import WeChatNotifier
        self.n = WeChatNotifier()
        self.n.initialize(message_hub=MagicMock(), container_center=MagicMock())

    def test_setting_off(self):
        self.n._notify_low_stock = False
        result = self.n.notify_low_stock({'material': '钢板', 'quantity': 5})
        assert result is False

    def test_no_hub(self):
        self.n._message_hub = None
        result = self.n.notify_low_stock({'material': '钢板', 'quantity': 5})
        assert result is False

    def test_success(self):
        self.n._message_hub.broadcast.return_value = True
        result = self.n.notify_low_stock({
            'material': '钢板', 'quantity': 5, 'threshold': 10
        })
        assert result is True

    def test_exception(self):
        self.n._message_hub.broadcast.side_effect = Exception('err')
        result = self.n.notify_low_stock({'material': '钢板', 'quantity': 5})
        assert result is False


class TestCustomNotify:
    """自定义通知测试"""

    def setup_method(self):
        from services.notifier import WeChatNotifier
        self.n = WeChatNotifier()
        self.n.initialize(message_hub=MagicMock(), container_center=MagicMock())

    def test_disabled(self):
        self.n._enabled = False
        assert self.n.send_custom_notification('OP001', 'test') is False

    def test_no_hub(self):
        self.n._message_hub = None
        assert self.n.send_custom_notification('OP001', 'test') is False

    def test_success(self):
        self.n._message_hub.send_to_user.return_value = True
        assert self.n.send_custom_notification('OP001', 'test') is True

    def test_exception(self):
        self.n._message_hub.send_to_user.side_effect = Exception('err')
        assert self.n.send_custom_notification('OP001', 'test') is False
