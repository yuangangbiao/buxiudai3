# -*- coding: utf-8 -*-
"""
publish_mode_manager.py 单元测试
"""

import pytest


class TestPublishModeManager:

    def test_manager_init(self):
        """验证管理器初始化"""
        from publish_mode_manager import PublishModeManager

        mgr = PublishModeManager()
        assert mgr is not None
        assert hasattr(mgr, 'set_mode')
        assert hasattr(mgr, 'get_mode')

    def test_valid_modes(self):
        """验证有效模式定义"""
        from publish_mode_manager import PublishModeManager

        assert 'manual' in PublishModeManager.VALID_MODES
        assert 'auto' in PublishModeManager.VALID_MODES

    def test_set_mode_manual(self):
        """验证设置手动模式"""
        from publish_mode_manager import PublishModeManager, reset_publish_mode_manager

        reset_publish_mode_manager()
        mgr = PublishModeManager()

        result = mgr.set_mode('manual')
        assert result
        assert mgr.get_mode() == 'manual'
        assert mgr.is_manual_mode()
        assert not mgr.is_auto_mode()

    def test_set_mode_auto(self):
        """验证设置自动模式"""
        from publish_mode_manager import PublishModeManager, reset_publish_mode_manager

        reset_publish_mode_manager()
        mgr = PublishModeManager()

        result = mgr.set_mode('auto')
        assert result
        assert mgr.get_mode() == 'auto'
        assert not mgr.is_manual_mode()
        assert mgr.is_auto_mode()

    def test_set_mode_invalid(self):
        """验证无效模式处理"""
        from publish_mode_manager import PublishModeManager, reset_publish_mode_manager

        reset_publish_mode_manager()
        mgr = PublishModeManager()

        with pytest.raises(ValueError):
            mgr.set_mode('invalid_mode')

    def test_set_mode_same(self):
        """验证设置相同模式"""
        from publish_mode_manager import PublishModeManager, reset_publish_mode_manager

        reset_publish_mode_manager()
        mgr = PublishModeManager()

        mgr.set_mode('manual')
        result = mgr.set_mode('manual')
        assert result

    def test_toggle_mode(self):
        """验证切换模式"""
        from publish_mode_manager import PublishModeManager, reset_publish_mode_manager

        reset_publish_mode_manager()
        mgr = PublishModeManager()

        mgr.set_mode('manual')
        assert mgr.is_manual_mode()

        mgr.toggle_mode()
        assert mgr.is_auto_mode()

        mgr.toggle_mode()
        assert mgr.is_manual_mode()

    def test_subscribe_unsubscribe(self):
        """验证订阅/取消订阅"""
        from publish_mode_manager import PublishModeManager, reset_publish_mode_manager

        reset_publish_mode_manager()
        mgr = PublishModeManager()

        callback_called = []

        def callback(new_mode, old_mode):
            callback_called.append((new_mode, old_mode))

        mgr.subscribe(callback)
        mgr.set_mode('auto')
        mgr.unsubscribe(callback)
        mgr.set_mode('manual')

        assert len(callback_called) == 1
        assert callback_called[0] == ('auto', 'manual')

    def test_reset(self):
        """验证重置为默认模式"""
        from publish_mode_manager import PublishModeManager, reset_publish_mode_manager

        reset_publish_mode_manager()
        mgr = PublishModeManager()

        default_mode = mgr._default_mode
        mgr.set_mode('auto' if default_mode == 'manual' else 'manual')
        mgr.reset()

        assert mgr.get_mode() == default_mode


class TestPublishModeManagerSingleton:

    def test_get_publish_mode_manager(self):
        """验证获取全局实例"""
        from publish_mode_manager import get_publish_mode_manager, reset_publish_mode_manager

        reset_publish_mode_manager()
        mgr1 = get_publish_mode_manager()
        mgr2 = get_publish_mode_manager()
        assert mgr1 is mgr2

    def test_reset_publish_mode_manager(self):
        """验证重置功能"""
        from publish_mode_manager import get_publish_mode_manager, reset_publish_mode_manager

        mgr1 = get_publish_mode_manager()
        reset_publish_mode_manager()
        mgr2 = get_publish_mode_manager()
        assert mgr1 is not mgr2
