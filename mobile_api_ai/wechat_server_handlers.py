# -*- coding: utf-8 -*-
"""
微信消息处理器 - 供云端轮询调用

从云端获取的微信消息由此处理
复用 wechat_server.py 的 WechatMessageHandler 进行处理
"""
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

# 全局消息处理器引用（由 wechat_server.py 设置）
_wechat_handler = None
_container_center = None

def set_wechat_handler(handler, container_center):
    """
    设置微信消息处理器（由 wechat_server.py 启动时调用）

    Args:
        handler: WechatMessageHandler 实例
        container_center: 容器中心实例
    """
    global _wechat_handler, _container_center
    _wechat_handler = handler
    _container_center = container_center
    logger.info('[云端处理器] 已绑定 WechatMessageHandler')

def handle_cloud_message(data):
    """
    处理从云端轮询来的微信消息

    Args:
        data: 微信消息字典，包含:
            - MsgType: 消息类型 (text/image/voice/video)
            - Content: 文本内容
            - FromUserName: 发送者用户名
            - MsgId: 消息ID
            - Event: 事件类型（事件消息时）
            - etc.
    """
    # 兼容数据库字段名（_msg_store 用 user_id/content/msg_type）
    # 转成 handle_cloud_message 期望的 FromUserName/Content/MsgType
    field_map = {
        'user_id': 'FromUserName',
        'content': 'Content',
        'msg_type': 'MsgType',
        'msg_id': 'MsgId',
    }
    for db_key, wx_key in field_map.items():
        if db_key in data and wx_key not in data:
            data[wx_key] = data[db_key]

    try:
        msg_type = data.get('MsgType', 'text')
        from_user = data.get('FromUserName', '')
        content = data.get('Content', '')
        msg_id = data.get('MsgId', '')

        logger.info(f'[云端消息] 类型={msg_type}, 用户={from_user}, 内容={content[:50]}')

        if msg_type == 'text':
            handle_text_message(data)
        elif msg_type == 'image':
            handle_image_message(data)
        elif msg_type == 'voice':
            handle_voice_message(data)
        elif msg_type == 'event':
            handle_event_message(data)
        else:
            logger.info(f'[云端消息] 未处理的消息类型: {msg_type}')

    except Exception as e:
        logger.error(f'[云端消息] 处理异常: {e}', exc_info=True)

def handle_text_message(data):
    """处理文本消息"""
    content = data.get('Content', '').strip()
    from_user = data.get('FromUserName', '')
    xml_str = data.get('xml_str', '')

    if not content:
        return

    logger.info(f'[文本消息] from={from_user}, content={content}')

    if not _wechat_handler or not _container_center:
        logger.warning('[文本消息] 处理器未初始化')
        return

    try:
        if _wechat_handler.handle_confirmation(from_user, content):
            logger.info('[文本消息] 已处理确认指令')
            return

        _wechat_handler.handle_command(from_user, content, _container_center, xml_str)

    except Exception as e:
        logger.error(f'[文本消息] 处理异常: {e}', exc_info=True)

def handle_image_message(data):
    """处理图片消息"""
    pic_url = data.get('PicUrl', '')
    media_id = data.get('MediaId', '')
    from_user = data.get('FromUserName', '')

    logger.info(f'[图片消息] from={from_user}, media_id={media_id}')

def handle_voice_message(data):
    """处理语音消息"""
    media_id = data.get('MediaId', '')
    recognition = data.get('Recognition', '')
    from_user = data.get('FromUserName', '')

    logger.info(f'[语音消息] from={from_user}, recognition={recognition}')

def handle_event_message(data):
    """处理事件消息"""
    event = data.get('Event', '')
    from_user = data.get('FromUserName', '')
    event_key = data.get('EventKey', '')

    logger.info(f'[事件消息] event={event}, from={from_user}, key={event_key}')
