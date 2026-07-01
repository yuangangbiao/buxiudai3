# -*- coding: utf-8 -*-
"""
机器人工厂模块

统一创建和管理不同类型的机器人实例
"""

import os
import threading
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import logging

from bots.base import BaseBot, BotType
from bots.group_bot import GroupBot
from bots.app_bot import AppBot

logger = logging.getLogger(__name__)


class BotFactory:
    """
    机器人工厂

    单例模式，线程安全
    统一创建和管理机器人实例
    """

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._group_bot: Optional[GroupBot] = None
        self._app_bot: Optional[AppBot] = None
        self._config: Dict[str, Any] = {}
        self._initialized = True

        self._load_config()

    def _load_config(self):
        """从环境变量加载配置"""
        load_dotenv()

        self._config = {
            'webhook_url': os.getenv('WECHAT_WORK_BOT_URL'),
            'corp_id': os.getenv('WECHAT_CORP_ID'),
            'agent_id': os.getenv('WECHAT_AGENT_ID'),
            'secret': os.getenv('WECHAT_SECRET'),
            'token': os.getenv('WECHAT_TOKEN'),
        }

        logger.info(f"[BotFactory] 配置加载完成")

    def create_group_bot(self, webhook_url: str = None) -> GroupBot:
        """
        创建群机器人

        Args:
            webhook_url: Webhook URL，如果为None则使用配置中的URL

        Returns:
            GroupBot: 群机器人实例
        """
        url = webhook_url or self._config.get('webhook_url')

        if not url:
            logger.warning("[BotFactory] 群机器人 Webhook URL 未配置")
            return None

        self._group_bot = GroupBot(url)
        logger.info("[BotFactory] 群机器人创建成功")
        return self._group_bot

    def create_app_bot(self, corp_id: str = None, agent_id: str = None,
                       secret: str = None) -> Optional[AppBot]:
        """
        创建应用机器人

        Args:
            corp_id: 企业ID，如果为None则使用配置中的值
            agent_id: 应用AgentID
            secret: 应用Secret

        Returns:
            AppBot: 应用机器人实例，或None
        """
        cid = corp_id or self._config.get('corp_id')
        aid = agent_id or self._config.get('agent_id')
        sec = secret or self._config.get('secret')

        if not cid or not aid or not sec:
            logger.warning("[BotFactory] 应用机器人配置不完整")
            return None

        self._app_bot = AppBot(cid, aid, sec)
        logger.info("[BotFactory] 应用机器人创建成功")
        return self._app_bot

    def get_group_bot(self) -> Optional[GroupBot]:
        """
        获取已创建的群机器人实例

        Returns:
            GroupBot: 群机器人实例，如果未创建则返回None
        """
        if self._group_bot is None:
            return self.create_group_bot()
        return self._group_bot

    def get_app_bot(self) -> Optional[AppBot]:
        """
        获取已创建的应用机器人实例

        Returns:
            AppBot: 应用机器人实例，如果未创建则返回None
        """
        if self._app_bot is None:
            return self.create_app_bot()
        return self._app_bot

    def get_default_bot(self) -> BaseBot:
        """
        获取默认机器人

        优先级：AppBot > GroupBot

        Returns:
            BaseBot: 默认机器人实例
        """
        app_bot = self.get_app_bot()
        if app_bot and app_bot.is_connected():
            return app_bot

        group_bot = self.get_group_bot()
        if group_bot and group_bot.is_connected():
            return group_bot

        logger.warning("[BotFactory] 没有可用的机器人实例")
        return None

    def get_bot_by_type(self, bot_type: BotType) -> Optional[BaseBot]:
        """
        根据类型获取机器人

        Args:
            bot_type: 机器人类型

        Returns:
            BaseBot: 机器人实例
        """
        if bot_type == BotType.GROUP:
            return self.get_group_bot()
        elif bot_type == BotType.APP:
            return self.get_app_bot()
        else:
            logger.warning(f"[BotFactory] 不支持的机器人类型: {bot_type}")
            return None

    def is_configured(self) -> bool:
        """
        检查是否已配置至少一种机器人

        Returns:
            bool: 是否已配置
        """
        return bool(self._config.get('webhook_url') or
                   (self._config.get('corp_id') and
                    self._config.get('agent_id') and
                    self._config.get('secret')))

    def get_config(self) -> Dict[str, Any]:
        """
        获取配置信息

        Returns:
            Dict: 配置字典（不包含敏感信息）
        """
        return {
            'webhook_url_configured': bool(self._config.get('webhook_url')),
            'app_bot_configured': bool(self._config.get('corp_id') and
                                      self._config.get('agent_id') and
                                      self._config.get('secret')),
            'group_bot_connected': self._group_bot.is_connected() if self._group_bot else False,
            'app_bot_connected': self._app_bot.is_connected() if self._app_bot else False,
        }

    def reset(self):
        """重置工厂状态（用于测试）"""
        self._group_bot = None
        self._app_bot = None
        self._initialized = False


_factory_instance: Optional[BotFactory] = None


def get_factory() -> BotFactory:
    """
    获取机器人工厂单例

    Returns:
        BotFactory: 工厂实例
    """
    global _factory_instance
    if _factory_instance is None:
        _factory_instance = BotFactory()
    return _factory_instance


def create_group_bot(webhook_url: str = None) -> GroupBot:
    """便捷函数：创建群机器人"""
    return get_factory().create_group_bot(webhook_url)


def create_app_bot(corp_id: str = None, agent_id: str = None,
                   secret: str = None) -> Optional[AppBot]:
    """便捷函数：创建应用机器人"""
    return get_factory().create_app_bot(corp_id, agent_id, secret)


def get_default_bot() -> BaseBot:
    """便捷函数：获取默认机器人"""
    return get_factory().get_default_bot()
