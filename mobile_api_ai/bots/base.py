# -*- coding: utf-8 -*-
"""
机器人基类模块

定义所有机器人的通用接口
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


class BotType(Enum):
    """机器人类型枚举"""
    GROUP = 'group'
    APP = 'app'
    CORP = 'corp'
    UNKNOWN = 'unknown'


class BaseBot(ABC):
    """
    机器人基类

    定义所有机器人的通用接口
    """

    def __init__(self, bot_type: BotType = BotType.UNKNOWN):
        self.bot_type = bot_type
        self.name = self.__class__.__name__

    @abstractmethod
    def send_text(self, content: str, **kwargs) -> bool:
        """
        发送文本消息

        Args:
            content: 消息内容
            **kwargs: 可选参数，如 target_user, target_group 等

        Returns:
            bool: 发送是否成功
        """
        pass

    @abstractmethod
    def send_markdown(self, content: str, **kwargs) -> bool:
        """
        发送Markdown消息

        Args:
            content: Markdown格式内容
            **kwargs: 可选参数

        Returns:
            bool: 发送是否成功
        """
        pass

    @abstractmethod
    def send_news(self, articles: List[Dict[str, Any]], **kwargs) -> bool:
        """
        发送图文消息

        Args:
            articles: 图文列表，每个元素包含 title, description, url, picurl

        Returns:
            bool: 发送是否成功
        """
        pass

    def send_image(self, image_path: str, **kwargs) -> bool:
        """
        发送图片消息

        Args:
            image_path: 图片路径或URL

        Returns:
            bool: 发送是否成功
        """
        raise NotImplementedError(f"{self.name} does not support send_image")

    def send_template_card(self, card_data: Dict, **kwargs) -> bool:
        """
        发送模板卡片消息

        Args:
            card_data: 卡片数据

        Returns:
            bool: 发送是否成功
        """
        raise NotImplementedError(f"{self.name} does not support send_template_card")

    def receive(self, request_data: Dict) -> Optional[Dict]:
        """
        接收并处理消息（框架方法）

        Args:
            request_data: 请求数据

        Returns:
            处理结果或None
        """
        msg_type = request_data.get('msg_type', 'text')
        content = request_data.get('content', '')
        from_user = request_data.get('from_user', 'unknown')

        logger.info(f"[{self.name}] 收到消息 from={from_user}, type={msg_type}")

        return {
            'bot_type': self.bot_type.value,
            'received': True,
            'msg_type': msg_type,
            'content': content,
        }

    def is_connected(self) -> bool:
        """
        检查机器人是否已连接

        Returns:
            bool: 是否已连接
        """
        return True

    def get_info(self) -> Dict:
        """
        获取机器人信息

        Returns:
            Dict: 机器人信息
        """
        return {
            'type': self.bot_type.value,
            'name': self.name,
            'connected': self.is_connected(),
        }


class GroupBot(BaseBot):
    """群机器人基类"""

    def __init__(self):
        super().__init__(BotType.GROUP)


class AppBot(BaseBot):
    """应用机器人基类"""

    def __init__(self):
        super().__init__(BotType.APP)
