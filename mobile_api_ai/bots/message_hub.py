# -*- coding: utf-8 -*-
"""
消息中心模块

统一管理和分发消息
"""

import threading
from typing import Dict, List, Callable, Any, Optional
from datetime import datetime
import logging

from bots.base import BaseBot, BotType

logger = logging.getLogger(__name__)


class MessageHub:
    """
    消息中心

    负责：
    - 消息路由和分发
    - 注册消息处理器
    - 广播消息
    - 消息队列管理
    """

    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        self._bots: Dict[BotType, BaseBot] = {}
        self._queue: List[Dict] = []
        self._queue_lock = threading.Lock()
        self._handlers_lock = threading.Lock()

    def register_bot(self, bot_type: BotType, bot: BaseBot):
        """
        注册机器人

        Args:
            bot_type: 机器人类型
            bot: 机器人实例
        """
        self._bots[bot_type] = bot
        logger.info(f"[MessageHub] 机器人注册: {bot_type.value}")

    def get_bot(self, bot_type: BotType = None) -> Optional[BaseBot]:
        """
        获取机器人

        Args:
            bot_type: 机器人类型，如果为None则返回默认机器人

        Returns:
            BaseBot: 机器人实例
        """
        if bot_type:
            return self._bots.get(bot_type)

        for bot in [BotType.APP, BotType.GROUP]:
            if bot in self._bots and self._bots[bot].is_connected():
                return self._bots[bot]

        return None

    def register_handler(self, event_type: str, handler: Callable):
        """
        注册消息处理器

        Args:
            event_type: 事件类型，如 'message', 'command', 'callback'
            handler: 处理函数，接收消息字典，返回处理结果
        """
        with self._handlers_lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)
        logger.info(f"[MessageHub] 处理器注册: {event_type}")

    def unregister_handler(self, event_type: str, handler: Callable):
        """
        取消注册消息处理器

        Args:
            event_type: 事件类型
            handler: 处理函数
        """
        with self._handlers_lock:
            if event_type in self._handlers:
                try:
                    self._handlers[event_type].remove(handler)
                    logger.info(f"[MessageHub] 处理器取消注册: {event_type}")
                except ValueError:
                    pass

    def dispatch(self, message: Dict) -> Dict:
        """
        分发消息到注册的处理器

        Args:
            message: 消息字典，包含:
                - msg_type: 消息类型
                - content: 消息内容
                - from_user: 发送者
                - other fields...

        Returns:
            Dict: 处理结果
        """
        msg_type = message.get('msg_type', 'unknown')
        start_time = datetime.now()

        result = {
            'success': False,
            'msg_type': msg_type,
            'processed': False,
            'results': []
        }

        handlers = self._handlers.get(msg_type, [])
        handlers.extend(self._handlers.get('*', []))

        if not handlers:
            logger.debug(f"[MessageHub] 没有注册的消息处理器: {msg_type}")
            result['error'] = 'No handler registered'
            return result

        for handler in handlers:
            try:
                handler_result = handler(message)
                result['results'].append(handler_result)
                if handler_result and handler_result.get('success'):
                    result['processed'] = True
            except Exception as e:
                logger.error(f"[MessageHub] 处理器执行异常: {e}")
                result['results'].append({'success': False, 'error': str(e)})

        result['success'] = result['processed']
        result['duration_ms'] = (datetime.now() - start_time).total_seconds() * 1000

        return result

    def broadcast(self, content: str, bot_type: BotType = BotType.GROUP,
                  **kwargs) -> bool:
        """
        广播消息

        Args:
            content: 消息内容
            bot_type: 使用的机器人类型
            **kwargs: 额外参数

        Returns:
            bool: 发送是否成功
        """
        bot = self.get_bot(bot_type)
        if not bot:
            logger.warning(f"[MessageHub] 广播失败: 机器人不可用 {bot_type}")
            return False

        try:
            if 'markdown' in content.lower() or content.startswith('#'):
                return bot.send_markdown(content, **kwargs)
            else:
                return bot.send_text(content, **kwargs)
        except Exception as e:
            logger.error(f"[MessageHub] 广播异常: {e}")
            return False

    def send_to_user(self, user_id: str, content: str, bot_type: BotType = BotType.APP,
                     **kwargs) -> bool:
        """
        发送消息给指定用户

        Args:
            user_id: 用户ID
            content: 消息内容
            bot_type: 使用的机器人类型
            **kwargs: 额外参数

        Returns:
            bool: 发送是否成功
        """
        bot = self.get_bot(bot_type)
        if not bot:
            logger.warning(f"[MessageHub] 发送失败: 机器人不可用 {bot_type}")
            return False

        try:
            if hasattr(bot, 'send_text_to_user'):
                return bot.send_text_to_user(user_id, content)
            elif hasattr(bot, 'send_text'):
                return bot.send_text(content, user_id=user_id, **kwargs)
            else:
                logger.warning(f"[MessageHub] 机器人不支持发送消息")
                return False
        except Exception as e:
            logger.error(f"[MessageHub] 发送消息异常: {e}")
            return False

    def send_to_group(self, chat_id: str, content: str,
                      bot_type: BotType = BotType.GROUP, **kwargs) -> bool:
        """
        发送消息到群

        Args:
            chat_id: 群ID
            content: 消息内容
            bot_type: 使用的机器人类型
            **kwargs: 额外参数

        Returns:
            bool: 发送是否成功
        """
        bot = self.get_bot(bot_type)
        if not bot:
            logger.warning(f"[MessageHub] 发送失败: 机器人不可用 {bot_type}")
            return False

        try:
            if hasattr(bot, 'send_text_to_group'):
                return bot.send_text_to_group(chat_id, content)
            elif hasattr(bot, 'send_text'):
                return bot.send_text(content, **kwargs)
            else:
                logger.warning(f"[MessageHub] 机器人不支持发送消息")
                return False
        except Exception as e:
            logger.error(f"[MessageHub] 发送消息异常: {e}")
            return False

    def enqueue(self, message: Dict):
        """
        将消息加入队列

        Args:
            message: 消息字典
        """
        with self._queue_lock:
            message['_enqueued_at'] = datetime.now().isoformat()
            self._queue.append(message)
        logger.debug(f"[MessageHub] 消息入队，当前队列长度: {len(self._queue)}")

    def process_queue(self) -> int:
        """
        处理队列中的所有消息

        Returns:
            int: 处理的消息数量
        """
        processed = 0

        with self._queue_lock:
            queue = self._queue
            self._queue = []

        for message in queue:
            try:
                self.dispatch(message)
                processed += 1
            except Exception as e:
                logger.error(f"[MessageHub] 处理队列消息异常: {e}")

        logger.info(f"[MessageHub] 队列处理完成，处理了 {processed} 条消息")
        return processed

    def get_queue_size(self) -> int:
        """
        获取队列长度

        Returns:
            int: 队列中的消息数量
        """
        with self._queue_lock:
            return len(self._queue)


    def get_info(self) -> Dict:
        """获取消息中心信息"""
        return {
            'registered_bots': [bt.value for bt in self._bots.keys()],
            'handlers': {event: len(handlers) for event, handlers in self._handlers.items()},
            'queue_size': self.get_queue_size(),
        }


_hub_instance: Optional[MessageHub] = None
_hub_lock = threading.Lock()


def get_hub() -> MessageHub:
    """
    获取消息中心单例

    Returns:
        MessageHub: 消息中心实例
    """
    global _hub_instance
    if _hub_instance is None:
        with _hub_lock:
            if _hub_instance is None:
                _hub_instance = MessageHub()
    return _hub_instance
