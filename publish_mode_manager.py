# -*- coding: utf-8 -*-
"""
发布模式管理器 - Publish Mode Manager

管理手动/自动发布模式的切换

使用方式：
    from publish_mode_manager import PublishModeManager, get_publish_mode_manager

    # 获取管理器
    mgr = get_publish_mode_manager()

    # 设置模式
    mgr.set_mode('manual')  # 或 'auto'

    # 查询模式
    if mgr.is_manual_mode():
        print('当前模式: 手动')

    # 监听模式变更
    def on_mode_changed(mode):
        print(f'模式已切换为: {mode}')

    mgr.subscribe(on_mode_changed)
"""

import sys
import os
import logging
from typing import Optional, Callable, List

logger = logging.getLogger(__name__)

MOBILE_API_AI_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'mobile_api_ai')
if MOBILE_API_AI_PATH not in sys.path:
    sys.path.insert(0, MOBILE_API_AI_PATH)


class PublishModeManager:
    """
    发布模式管理器

    职责：
        - 管理手动/自动发布模式
        - 提供模式切换接口
        - 通知模式变更事件
    """

    MODE_MANUAL = 'manual'
    MODE_AUTO = 'auto'
    VALID_MODES = [MODE_MANUAL, MODE_AUTO]

    def __init__(self):
        """
        初始化发布模式管理器
        """
        self._load_config()
        self._mode = self._default_mode
        self._subscribers: List[Callable] = []
        self._load_saved_mode()

    def _load_config(self) -> None:
        """
        加载配置
        """
        try:
            from modular_config import ModularConfig
            config = ModularConfig()
            mp_config = config.get_config('manual_publish', {})
            self._enabled = mp_config.get('enabled', True)
            self._default_mode = mp_config.get('default_mode', self.MODE_MANUAL)
            self._confirm_before = mp_config.get('confirm_before_publish', True)
        except Exception:
            self._enabled = True
            self._default_mode = self.MODE_MANUAL
            self._confirm_before = True

    def _load_saved_mode(self) -> None:
        """
        加载保存的模式
        """
        try:
            from modular_config import ModularConfig
            config = ModularConfig()
            saved_mode = config.get_config('manual_publish.current_mode', None)
            if saved_mode in self.VALID_MODES:
                self._mode = saved_mode
                logger.info(f'[发布模式] 加载保存的模式: {self._mode}')
            else:
                self._mode = self._default_mode
        except Exception:
            self._mode = self._default_mode

    def _save_mode(self, mode: str) -> bool:
        """
        保存当前模式到配置

        Args:
            mode: 模式

        Returns:
            是否成功
        """
        try:
            from modular_config import ModularConfig
            config = ModularConfig()
            config.set_config('manual_publish.current_mode', mode)
            config.save_config()
            return True
        except Exception as e:
            logger.warning(f'[发布模式] 保存模式失败: {e}')
            return False

    def _notify_subscribers(self, old_mode: str, new_mode: str) -> None:
        """
        通知订阅者模式变更

        Args:
            old_mode: 旧模式
            new_mode: 新模式
        """
        for callback in self._subscribers:
            try:
                callback(new_mode, old_mode)
            except Exception as e:
                logger.warning(f'[发布模式] 通知订阅者失败: {e}')

        self._notify_event_bus(new_mode, old_mode)

    def _notify_event_bus(self, new_mode: str, old_mode: str) -> None:
        """
        通知EventBus

        Args:
            new_mode: 新模式
            old_mode: 旧模式
        """
        try:
            from event_bus import EventBus
            EventBus.publish('MODE_CHANGED', {
                'new_mode': new_mode,
                'old_mode': old_mode
            })
        except ImportError:
            logger.warning('[发布模式] EventBus不可用')
        except Exception as e:
            logger.warning(f'[发布模式] EventBus通知失败: {e}')

    def set_mode(self, mode: str) -> bool:
        """
        设置发布模式

        Args:
            mode: 模式 ('manual' 或 'auto')

        Returns:
            是否成功

        Raises:
            ValueError: 无效模式
        """
        if mode not in self.VALID_MODES:
            raise ValueError(f'无效发布模式: {mode}。有效值: {self.VALID_MODES}')

        if mode == self._mode:
            logger.info(f'[发布模式] 模式未变更: {mode}')
            return True

        old_mode = self._mode
        self._mode = mode

        if self._save_mode(mode):
            logger.info(f'[发布模式] 模式切换成功: {old_mode} -> {mode}')
            self._notify_subscribers(old_mode, mode)
            return True

        self._mode = old_mode
        return False

    def get_mode(self) -> str:
        """
        获取当前模式

        Returns:
            当前模式
        """
        return self._mode

    def is_manual_mode(self) -> bool:
        """
        检查是否为手动模式

        Returns:
            是否手动模式
        """
        return self._mode == self.MODE_MANUAL

    def is_auto_mode(self) -> bool:
        """
        检查是否为自动模式

        Returns:
            是否自动模式
        """
        return self._mode == self.MODE_AUTO

    def is_enabled(self) -> bool:
        """
        检查功能是否启用

        Returns:
            是否启用
        """
        return self._enabled

    def get_confirm_before_publish(self) -> bool:
        """
        获取发布前确认设置

        Returns:
            是否需要确认
        """
        return self._confirm_before

    def toggle_mode(self) -> bool:
        """
        切换发布模式

        Returns:
            切换后的模式
        """
        new_mode = self.MODE_AUTO if self._mode == self.MODE_MANUAL else self.MODE_MANUAL
        self.set_mode(new_mode)
        return self._mode == new_mode

    def subscribe(self, callback: Callable) -> None:
        """
        订阅模式变更

        Args:
            callback: 回调函数，签名: (new_mode: str, old_mode: str)
        """
        if callback not in self._subscribers:
            self._subscribers.append(callback)
            logger.info(f'[发布模式] 订阅者添加成功，当前订阅数: {len(self._subscribers)}')

    def unsubscribe(self, callback: Callable) -> None:
        """
        取消订阅

        Args:
            callback: 回调函数
        """
        if callback in self._subscribers:
            self._subscribers.remove(callback)
            logger.info(f'[发布模式] 订阅者移除成功，当前订阅数: {len(self._subscribers)}')

    def reset(self) -> bool:
        """
        重置为默认模式

        Returns:
            是否成功
        """
        return self.set_mode(self._default_mode)


_publish_mode_manager_instance: Optional['PublishModeManager'] = None


def get_publish_mode_manager() -> 'PublishModeManager':
    """
    获取全局发布模式管理器实例（单例）

    Returns:
        PublishModeManager实例
    """
    global _publish_mode_manager_instance
    if _publish_mode_manager_instance is None:
        _publish_mode_manager_instance = PublishModeManager()
    return _publish_mode_manager_instance


def reset_publish_mode_manager() -> None:
    """
    重置全局发布模式管理器实例
    """
    global _publish_mode_manager_instance
    _publish_mode_manager_instance = None


def demo() -> None:
    """
    演示用法
    """
    print('=' * 60)
    print('发布模式管理器演示')
    print('=' * 60)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    mgr = get_publish_mode_manager()

    print(f'\n[1] 当前模式: {mgr.get_mode()}')

    def on_mode_changed(new_mode, old_mode):
        print(f'   模式变更回调: {old_mode} -> {new_mode}')

    mgr.subscribe(on_mode_changed)

    print('\n[2] 切换到手动模式...')
    mgr.set_mode('manual')
    print(f'   当前模式: {mgr.get_mode()}')
    print(f'   是手动模式: {mgr.is_manual_mode()}')

    print('\n[3] 切换到自动模式...')
    mgr.set_mode('auto')
    print(f'   当前模式: {mgr.get_mode()}')
    print(f'   是自动模式: {mgr.is_auto_mode()}')

    print('\n[4] 切换模式...')
    mgr.toggle_mode()
    print(f'   切换后模式: {mgr.get_mode()}')

    print('\n[5] 尝试设置无效模式...')
    try:
        mgr.set_mode('invalid')
    except ValueError as e:
        print(f'   捕获异常: {e}')

    print('\n' + '=' * 60)
    print('演示完成！')
    print('=' * 60)


if __name__ == '__main__':
    demo()
