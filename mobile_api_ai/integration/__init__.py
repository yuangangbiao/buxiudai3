# -*- coding: utf-8 -*-
"""
集成服务模块
用于容器中心与企业微信、桌面端等的通信
"""
from .wechat_notifier import WeChatNotifier, TaskPollingNotifier, wechat_notifier
from .desktop_callback import DesktopCallbackManager, DesktopClientListener, desktop_callback_manager
from .instruction_handler import (
    InstructionParser, ResponseGenerator, UnifiedInstructionHandler,
    ParsedInstruction, InstructionSource, InstructionType,
    instruction_handler
)
__all__ = [
    'WeChatNotifier',
    'TaskPollingNotifier',
    'wechat_notifier',
    'DesktopCallbackManager',
    'DesktopClientListener',
    'desktop_callback_manager',
    'InstructionParser',
    'ResponseGenerator',
    'UnifiedInstructionHandler',
    'ParsedInstruction',
    'InstructionSource',
    'InstructionType',
    'instruction_handler',
]
