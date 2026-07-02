# -*- coding: utf-8 -*-
"""
[v3.6 迁移] 桌面端回调服务

DEPRECATED: 请使用 container_center.desktop_callback
此文件保留用于向后兼容，2026-12-31 将删除
"""
from container_center.desktop_callback import (
    DesktopCallbackManager,
    DesktopClientListener,
    desktop_callback_manager,
)

__all__ = [
    'DesktopCallbackManager',
    'DesktopClientListener',
    'desktop_callback_manager',
]
