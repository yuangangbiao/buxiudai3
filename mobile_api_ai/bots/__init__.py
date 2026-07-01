# -*- coding: utf-8 -*-
"""
企业微信机器人模块

提供统一的机器人接口，支持：
- GroupBot: 群机器人（Webhook方式）
- AppBot: 应用机器人（企业微信应用API）
"""

from bots.base import BaseBot, BotType
from bots.group_bot import GroupBot
from bots.app_bot import AppBot
from bots.factory import BotFactory
from bots.message_hub import MessageHub

__all__ = [
    'BaseBot',
    'BotType',
    'GroupBot',
    'AppBot',
    'BotFactory',
    'MessageHub',
]
