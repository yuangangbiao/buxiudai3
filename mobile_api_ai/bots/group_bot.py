# -*- coding: utf-8 -*-
"""
群机器人实现模块

基于企业微信群机器人的 Incoming Webhook 方式
"""

import requests
from typing import List, Dict, Any, Optional
import logging
import os

from bots.base import BaseBot
from circuit_breaker_integration import circuit_protected
from core.config import MAX_TEXT_LENGTH
from fault_tolerance import fault_tolerance

logger = logging.getLogger(__name__)


class GroupBot(BaseBot):
    """
    企业微信群机器人

    使用 Incoming Webhook 方式发送消息到群聊
    """

    MAX_TEXT_LENGTH = MAX_TEXT_LENGTH
    MAX_CARD_TITLE_LENGTH = 20
    MAX_CARD_DESCRIPTION_LENGTH = 200

    def __init__(self, webhook_url: str):
        """
        初始化群机器人

        Args:
            webhook_url: 企业微信群机器人的 Webhook URL
        """
        super().__init__()
        self.webhook_url = webhook_url
        self.cloud_host = os.getenv('WECHAT_CLOUD_HOST', '').strip()
        self.cloud_api_key = os.getenv('WECHAT_CLOUD_API_KEY', '')
        self.name = 'GroupBot'

    @circuit_protected("groupbot_request")
    def _do_request(self, payload: dict) -> Optional[dict]:
        """
        执行请求，支持云端代理转发

        Args:
            payload: 请求体

        Returns:
            Optional[dict]: 响应结果
        """
        if self.cloud_host:
            proxy_url = f"{self.cloud_host.rstrip('/')}/api/wechat/proxy_send"
            proxy_payload = {
                **payload,
                '_webhook_url': self.webhook_url,
                '_api_key': self.cloud_api_key
            }
            try:
                resp = fault_tolerance.execute_with_retry(lambda: requests.post(proxy_url, json=proxy_payload, timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10'))))
                if resp.status_code == 200:
                    return resp.json()
                logger.warning(f"云端代理返回非200状态码: {resp.status_code}, 降级到直连")
            except Exception as e:
                logger.warning(f"云端代理转发请求失败: {e}, 降级到直连")

        try:
            resp = fault_tolerance.execute_with_retry(lambda: requests.post(self.webhook_url, json=payload, timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10'))))
            return resp.json()
        except Exception as e:
            logger.warning(f"群机器人直连请求失败: {e}")
            return None

    def send_text(self, content: str, **kwargs) -> bool:
        """
        发送文本消息到群

        Args:
            content: 文本内容（最长2048字符）
            **kwargs: 可选参数

        Returns:
            bool: 发送是否成功
        """
        if not self.webhook_url:
            logger.warning("[GroupBot] Webhook URL 未配置")
            return False

        content = content[:self.MAX_TEXT_LENGTH]

        payload = {
            'msgtype': 'text',
            'text': {
                'content': content
            }
        }

        result = self._do_request(payload)

        if result and result.get('errcode') == 0:
            logger.info(f"[GroupBot] 文本消息发送成功")
            return True
        else:
            logger.error(f"[GroupBot] 发送失败: {result}")
            return False

    def send_markdown(self, content: str, **kwargs) -> bool:
        """
        发送Markdown消息到群

        企业微信支持的Markdown语法有限：
        - 标题 (# ## ### 等)
        - 加粗 (**text**)
        - 链接 ([text](url))
        - 引用 (> text)
        - 列表 (* 或 -)

        Args:
            content: Markdown格式内容
            **kwargs: 可选参数

        Returns:
            bool: 发送是否成功
        """
        if not self.webhook_url:
            logger.warning("[GroupBot] Webhook URL 未配置")
            return False

        content = content[:self.MAX_TEXT_LENGTH]

        payload = {
            'msgtype': 'markdown',
            'markdown': {
                'content': content
            }
        }

        result = self._do_request(payload)

        if result and result.get('errcode') == 0:
            logger.info(f"[GroupBot] Markdown消息发送成功")
            return True
        else:
            logger.error(f"[GroupBot] Markdown发送失败: {result}")
            return False

    def send_news(self, articles: List[Dict[str, Any]], **kwargs) -> bool:
        """
        发送图文消息到群

        Args:
            articles: 图文列表，每个元素包含:
                - title: 标题（必填，最多64字节）
                - description: 描述（可选，最多512字节）
                - url: 点击后跳转的链接
                - picurl: 图片链接（可选）

        Returns:
            bool: 发送是否成功
        """
        if not self.webhook_url:
            logger.warning("[GroupBot] Webhook URL 未配置")
            return False

        if not articles:
            logger.warning("[GroupBot] 图文列表为空")
            return False

        for article in articles:
            if 'title' in article:
                article['title'] = article['title'][:64]
            if 'description' in article:
                article['description'] = article['description'][:512]

        payload = {
            'msgtype': 'news',
            'news': {
                'articles': articles
            }
        }

        result = self._do_request(payload)

        if result and result.get('errcode') == 0:
            logger.info(f"[GroupBot] 图文消息发送成功")
            return True
        else:
            logger.error(f"[GroupBot] 图文发送失败: {result}")
            return False

    def send_image(self, image_path: str, **kwargs) -> bool:
        """
        发送图片消息到群

        注意：企业微信群机器人图片需要先上传到临时素材，
        这里提供简化实现（直接发送图片URL）

        Args:
            image_path: 图片URL或本地路径
            **kwargs: 可选参数

        Returns:
            bool: 发送是否成功
        """
        if not self.webhook_url:
            logger.warning("[GroupBot] Webhook URL 未配置")
            return False

        if image_path.startswith('http'):
            picurl = image_path
        else:
            logger.warning("[GroupBot] 群机器人不支持本地图片路径")
            return False

        payload = {
            'msgtype': 'image',
            'image': {
                'picurl': picurl
            }
        }

        result = self._do_request(payload)

        if result and result.get('errcode') == 0:
            logger.info(f"[GroupBot] 图片消息发送成功")
            return True
        else:
            logger.error(f"[GroupBot] 图片发送失败: {result}")
            return False

    def send_card(self, title: str, description: str, url: str = '',
                  btntxt: str = '', **kwargs) -> bool:
        """
        发送卡片消息（文本卡片）

        Args:
            title: 卡片标题
            description: 卡片描述
            url: 点击链接
            btntxt: 按钮文字

        Returns:
            bool: 发送是否成功
        """
        if not self.webhook_url:
            logger.warning("[GroupBot] Webhook URL 未配置")
            return False

        title = title[:self.MAX_CARD_TITLE_LENGTH]
        description = description[:self.MAX_CARD_DESCRIPTION_LENGTH]

        content = f"**{title}**\n\n{description}"

        if url:
            content += f"\n\n[查看详情]({url})"
        if btntxt:
            content += f"\n\n> [{btntxt}]({url})"

        return self.send_markdown(content)

    def upload_media(self, file_path: str, media_type: str = 'image') -> Optional[str]:
        """
        上传临时素材

        Args:
            file_path: 文件路径
            media_type: 素材类型 (image, voice, video, file)

        Returns:
            str: media_id 或 None
        """
        logger.warning("[GroupBot] 群机器人不支持上传临时素材接口")
        return None

    @circuit_protected("groupbot_connected")
    def is_connected(self) -> bool:
        """
        检查机器人是否已连接

        Returns:
            bool: 是否已连接
        """
        if not self.webhook_url:
            return False

        try:
            resp = fault_tolerance.execute_with_retry(lambda: requests.get(self.webhook_url, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5'))))
            return resp.status_code == 200
        except Exception as e:
            logger.debug(f"群机器人webhook连接检测失败: {e}")
            return True

    def get_info(self) -> Dict:
        """获取机器人信息"""
        return {
            'type': self.bot_type.value,
            'name': self.name,
            'connected': self.is_connected(),
            'webhook_url': self.webhook_url[:20] + '...' if self.webhook_url else None,
        }
