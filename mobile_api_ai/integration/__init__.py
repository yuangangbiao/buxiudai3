# -*- coding: utf-8 -*-
"""
[v3.6 迁移] 集成服务模块

DEPRECATED: 所有模块已迁移到新位置：
- wechat_notifier.py      → services/notifier.py (wechat_notifier 单例已指向新版)
- desktop_callback.py     → container_center/desktop_callback.py (别名重定向)
- instruction_handler.py  → services/instruction_handler.py (别名重定向)

此 __init__.py 保留用于向后兼容，2026-12-31 将删除
"""

from .wechat_notifier import (
    WeChatNotifier,
    TaskPollingNotifier,
)
from services.notifier import wechat_notifier as notifier_singleton
from .desktop_callback import (
    DesktopCallbackManager,
    DesktopClientListener,
    desktop_callback_manager,
)
from .instruction_handler import (
    InstructionSource,
    InstructionType,
    ParsedInstruction,
    InstructionParser,
    ResponseGenerator,
    UnifiedInstructionHandler,
    instruction_handler,
)

__all__ = [
    'WeChatNotifier',
    'TaskPollingNotifier',
    'wechat_notifier',
    'DesktopCallbackManager',
    'DesktopClientListener',
    'desktop_callback_manager',
    'InstructionSource',
    'InstructionType',
    'ParsedInstruction',
    'InstructionParser',
    'ResponseGenerator',
    'UnifiedInstructionHandler',
    'instruction_handler',
]
