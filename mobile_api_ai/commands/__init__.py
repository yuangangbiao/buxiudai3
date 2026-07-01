# -*- coding: utf-8 -*-
"""
指令管理模块

提供指令解析和执行功能
"""

from commands.base import BaseCommand, CommandResult
from commands.manager import CommandManager, get_command_manager

__all__ = [
    'BaseCommand',
    'CommandResult',
    'CommandManager',
    'get_command_manager',
]
