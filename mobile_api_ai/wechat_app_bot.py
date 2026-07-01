#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
企业微信应用机器人核心模块
支持外部群消息发送和用户识别
"""

import os
import requests
import json
import time
import hashlib
import base64
import logging
import re
from datetime import datetime
from typing import Optional
from urllib.parse import unquote
try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

logger = logging.getLogger(__name__)

class WeChatAppBot:
    def __init__(self, corp_id, agent_id, secret):
        self.corp_id = corp_id
        self.agent_id = agent_id
        self.secret = secret
        self.access_token = None
        self.token_expire_time = 0
    
    def get_access_token(self):
        """获取企业微信access_token"""
        now = int(time.time())
        if self.access_token and now < self.token_expire_time:
            return self.access_token
        
        url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={self.corp_id}&corpsecret={self.secret}"
        try:
            resp = requests.get(url, timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10')))
            result = resp.json()
            if result.get('errcode') == 0:
                self.access_token = result['access_token']
                self.token_expire_time = now + result.get('expires_in', 7200) - 300
                return self.access_token
            else:
                logger.warning(f"获取access_token失败: {result.get('errcode')}")
                return None
        except Exception as e:
            logger.error(f"获取access_token异常: {e}")
            return None
    
    def send_text(self, user_id, content):
        """
        发送文本消息（兼容接口，委托给 send_text_to_user）

        Args:
            user_id: 用户ID
            content: 消息内容

        Returns:
            bool: 是否发送成功
        """
        return self.send_text_to_user(user_id, content)

    def send_text_to_user(self, user_id, content):
        """发送文本消息给单个用户"""
        token = self.get_access_token()
        if not token:
            return False
        
        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
        data = {
            "touser": user_id,
            "msgtype": "text",
            "agentid": self.agent_id,
            "text": {
                "content": content
            },
            "safe": 0
        }
        
        try:
            resp = requests.post(url, json=data, timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10')), headers={'Content-Type': 'application/json; charset=utf-8'})
            result = resp.json()
            return result.get('errcode') == 0
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return False
    
    def send_text_to_group(self, chat_id, content):
        """发送文本消息到外部群"""
        token = self.get_access_token()
        if not token:
            return False
        
        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
        data = {
            "chatid": chat_id,
            "msgtype": "text",
            "agentid": self.agent_id,
            "text": {
                "content": content
            },
            "safe": 0
        }
        
        try:
            resp = requests.post(url, json=data, timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10')))
            result = resp.json()
            return result.get('errcode') == 0
        except Exception as e:
            logger.error(f"发送群消息失败: {e}")
            return False
    
    def send_news_message(self, user_id, articles):
        """发送图文消息给用户"""
        token = self.get_access_token()
        if not token:
            return False
        
        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
        data = {
            "touser": user_id,
            "msgtype": "news",
            "agentid": self.agent_id,
            "news": {
                "articles": articles
            },
            "safe": 0
        }
        
        try:
            resp = requests.post(url, json=data, timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10')))
            result = resp.json()
            return result.get('errcode') == 0
        except Exception as e:
            logger.error(f"发送图文消息失败: {e}")
            return False
    
    def get_user_info(self, user_id):
        """获取用户信息"""
        token = self.get_access_token()
        if not token:
            return None
        
        url = f"https://qyapi.weixin.qq.com/cgi-bin/user/get?access_token={token}&userid={user_id}"
        try:
            resp = requests.get(url, timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10')))
            result = resp.json()
            if result.get('errcode') == 0:
                return result
            logger.warning(f"获取用户信息API返回错误: {result.get('errcode')}")
            return None
        except Exception as e:
            logger.error(f"获取用户信息失败: {e}")
            return None
    
    def get_media(self, media_id: str) -> tuple:
        """
        下载媒体文件（语音、图片等）

        Args:
            media_id: 媒体文件ID

        Returns:
            (bytes, str): (文件内容, 文件名) 或 (None, None)
        """
        token = self.get_access_token()
        if not token:
            return None, None

        url = f"https://qyapi.weixin.qq.com/cgi-bin/media/get?access_token={token}&media_id={media_id}"
        try:
            resp = requests.get(url, timeout=int(os.environ.get('REQUEST_TIMEOUT_LONG', '15')))
            content_type = resp.headers.get('Content-Type', '')
            if 'application/json' in content_type:
                result = resp.json()
                logger.error(f"[WeChatAppBot] 下载媒体失败: {result}")
                return None, None
            content_disposition = resp.headers.get('Content-Disposition', '')
            filename = 'voice.amr'
            if 'filename=' in content_disposition:
                filename = content_disposition.split('filename=')[-1].strip('" ')
            return resp.content, filename
        except Exception as e:
            logger.error(f"[WeChatAppBot] 下载媒体异常: {e}")
            return None, None

    def get_group_member_list(self, chat_id: str) -> dict:
        """获取群会话成员列表（需要群ID）"""
        token = self.get_access_token()
        if not token:
            return None
        url = f"https://qyapi.weixin.qq.com/cgi-bin/externalcontact/groupchat/get?access_token={token}"
        try:
            resp = requests.post(url, json={"chat_id": chat_id}, timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10')))
            result = resp.json()
            if result.get('errcode') == 0:
                return result.get('group_chat', {})
            logger.warning(f"[WeChatAppBot] 获取群成员列表失败: errcode={result.get('errcode')}, errmsg={result.get('errmsg', '')}")
            return None
        except Exception as e:
            logger.error(f"[WeChatAppBot] 获取群成员列表异常: {e}")
            return None

    def get_external_contact_list(self):
        """获取外部联系人列表（企业微信应用可见的客户）"""
        token = self.get_access_token()
        if not token:
            return None
        url = f"https://qyapi.weixin.qq.com/cgi-bin/externalcontact/list?access_token={token}&userid={self.agent_id}"
        try:
            resp = requests.get(url, timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10')))
            result = resp.json()
            if result.get('errcode') == 0:
                return result.get('ExternalUserid', [])
            logger.warning(f"[WeChatAppBot] 获取外部联系人列表失败: errcode={result.get('errcode')}, errmsg={result.get('errmsg', '')}")
            return None
        except Exception as e:
            logger.error(f"[WeChatAppBot] 获取外部联系人列表异常: {e}")
            return None

    def get_external_contact_info(self, user_id: str) -> dict:
        """获取单个外部联系人详情"""
        token = self.get_access_token()
        if not token:
            return None
        url = f"https://qyapi.weixin.qq.com/cgi-bin/externalcontact/get?access_token={token}&external_userid={user_id}"
        try:
            resp = requests.get(url, timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10')))
            result = resp.json()
            if result.get('errcode') == 0:
                return result
            logger.warning(f"[WeChatAppBot] 获取外部联系人详情失败: errcode={result.get('errcode')}")
            return None
        except Exception as e:
            logger.error(f"[WeChatAppBot] 获取外部联系人详情异常: {e}")
            return None

    def process_callback(self, xml_data: bytes, token: str = None, aes_key: str = None,
                         msg_signature: str = None, timestamp: str = None, nonce: str = None) -> str:
        """
        处理企业微信回调

        Args:
            xml_data: 回调原始数据（bytes）
            token: 回调Token
            aes_key: 回调AES密钥
            msg_signature: 消息签名
            timestamp: 时间戳
            nonce: 随机数

        Returns:
            str: 'success' 表示成功，其他表示错误
        """
        try:
            xml_str = xml_data.decode('utf-8') if isinstance(xml_data, bytes) else xml_data
            logger.info(f"[WeChatAppBot] 收到回调: {xml_str[:200]}")

            if not aes_key or not msg_signature:
                logger.warning("[WeChatAppBot] 缺少加密参数，尝试解析明文")
                return self._parse_plain_message(xml_str)

            encrypt = self._extract_encrypt(xml_str)
            if not encrypt:
                logger.info("[WeChatAppBot] 无加密内容，返回success")
                return 'success'

            if token and aes_key:
                decrypted = self._decrypt_message(encrypt, token, aes_key, msg_signature, timestamp, nonce)
                logger.info(f"[WeChatAppBot] 解密后: {decrypted}")
                return self._parse_plain_message(decrypted)

            return 'success'
        except ValueError as e:
            logger.warning(f"[WeChatAppBot] 签名验证失败: {e}")
            return 'signature verification failed'
        except Exception as e:
            logger.error(f"[WeChatAppBot] 处理回调异常: {e}")
            return 'error'

    def _extract_encrypt(self, xml_str: str) -> Optional[str]:
        """从XML中提取加密内容"""
        match = re.search(r'<Encrypt><!\[CDATA\[(.*?)\]\]></Encrypt>', xml_str)
        return match.group(1) if match else None

    def _decrypt_message(self, encrypt: str, token: str, aes_key: str,
                         msg_signature: str, timestamp: str, nonce: str) -> str:
        """解密消息"""
        params = [token, timestamp or '', nonce or '', encrypt]
        params.sort()
        sha1 = hashlib.sha1()
        sha1.update(''.join(params).encode('utf-8'))
        computed = sha1.hexdigest()
        if computed != msg_signature:
            logger.warning(f"[WeChatAppBot] 签名不匹配")
            raise ValueError("signature mismatch")

        if not CRYPTO_AVAILABLE:
            raise RuntimeError("cryptography library not installed")

        try:
            aes_key_bytes = base64.b64decode(aes_key + '=')
            enc = base64.b64decode(encrypt)
        except Exception as e:
            logger.error(f"[WeChatAppBot] base64解码失败: {e}")
            raise ValueError("base64 decode failed")

        if len(enc) < 32:
            logger.error(f"[WeChatAppBot] 加密数据太短: {len(enc)} bytes")
            raise ValueError("encrypted data too short")

        iv = enc[:16]
        cipher = Cipher(algorithms.AES(aes_key_bytes), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted = decryptor.update(enc[16:]) + decryptor.finalize()

        if not decrypted:
            logger.error("[WeChatAppBot] 解密后数据为空")
            raise ValueError("decrypted data empty")

        pad_len = decrypted[-1]
        if pad_len < 1 or pad_len > 32 or pad_len > len(decrypted):
            logger.error(f"[WeChatAppBot] 无效的padding长度: {pad_len}, data_len={len(decrypted)}")
            raise ValueError("invalid padding length")

        decrypted = decrypted[:-pad_len]
        return decrypted.decode('utf-8')

    def _parse_plain_message(self, xml_str: str) -> str:
        """解析并回复消息"""
        content_match = re.search(r'<Content><!\[CDATA\[(.*?)\]\]></Content>', xml_str)
        user_match = re.search(r'<FromUserName><!\[CDATA\[(.*?)\]\]></FromUserName>', xml_str)
        msg_type_match = re.search(r'<MsgType><!\[CDATA\[(.*?)\]\]></MsgType>', xml_str)
        chat_id_match = re.search(r'<ChatID><!\[CDATA\[(.*?)\]\]></ChatID>', xml_str)

        content = (content_match.group(1) if content_match else '').strip()
        user_id = user_match.group(1) if user_match else ''
        msg_type = msg_type_match.group(1) if msg_type_match else 'text'
        chat_id = chat_id_match.group(1) if chat_id_match else ''

        logger.info(f"[WeChatAppBot] 消息解析: type={msg_type}, user={user_id}, chat={chat_id or '单聊'}, content={content[:100]}")

        if not content:
            logger.info("[WeChatAppBot] 空消息内容")
            return 'success'

        if content in ['帮助', 'help', 'h', '？', '?', 'Help']:
            reply = self._build_help_text()
            logger.info(f"[WeChatAppBot] 回复帮助信息给 {user_id}")
        elif content.startswith('报工'):
            reply = f"✅ 已收到您的报工指令：{content}\n正在处理中，请稍候..."
            logger.info(f"[WeChatAppBot] 收到报工指令: {content}")
        elif content.startswith('任务') or content in ['我的任务', '待办', 'task', 'tasks']:
            reply = f"📋 正在查询您的任务列表：{content}\n请稍候..."
            logger.info(f"[WeChatAppBot] 收到任务查询: {content}")
        elif content.startswith('查询') or content.startswith('查单') or content.startswith('搜'):
            reply = f"🔍 正在查询：{content}\n请稍候..."
            logger.info(f"[WeChatAppBot] 收到查询指令: {content}")
        elif content.startswith('确认') or content.startswith('收到'):
            reply = f"✅ 正在确认：{content}\n请稍候..."
            logger.info(f"[WeChatAppBot] 收到确认指令: {content}")
        elif content.startswith('取消') or content.startswith('撤销'):
            reply = f"🔄 正在处理取消请求：{content}\n请稍候..."
            logger.info(f"[WeChatAppBot] 收到取消指令: {content}")
        elif content.startswith('领料'):
            reply = f"📦 已收到领料申请：{content}\n正在处理中，请稍候..."
            logger.info(f"[WeChatAppBot] 收到领料指令: {content}")
        elif content.startswith('报修'):
            reply = f"🔧 已收到报修申请：{content}\n正在处理中，请稍候..."
            logger.info(f"[WeChatAppBot] 收到报修指令: {content}")
        elif content.startswith('质检') or content.startswith('检验'):
            order_no = content.replace('质检', '').replace('检验', '').strip()
            if order_no:
                reply = f"✅ 已收到质检申请：\n订单号: {order_no}\n正在发布质检任务..."
            else:
                reply = "📋 质检指令格式：\n`质检 订单号` - 提交质检任务\n`质检记录` - 查看质检记录\n`首检/巡检/终检 订单号` - 指定质检类型"
            logger.info(f"[WeChatAppBot] 收到质检指令: {content}")
        elif content.startswith('首检'):
            order_no = content.replace('首检', '').strip()
            if order_no:
                reply = f"✅ 已收到首检申请：\n订单号: {order_no}\n正在发布首检任务..."
            else:
                reply = "📋 首检指令格式：\n`首检 订单号` - 提交首检任务"
            logger.info(f"[WeChatAppBot] 收到首检指令: {content}")
        elif content.startswith('巡检'):
            order_no = content.replace('巡检', '').strip()
            if order_no:
                reply = f"✅ 已收到巡检申请：\n订单号: {order_no}\n正在发布巡检任务..."
            else:
                reply = "📋 巡检指令格式：\n`巡检 订单号` - 提交巡检任务"
            logger.info(f"[WeChatAppBot] 收到巡检指令: {content}")
        elif content.startswith('终检'):
            order_no = content.replace('终检', '').strip()
            if order_no:
                reply = f"✅ 已收到终检申请：\n订单号: {order_no}\n正在发布终检任务..."
            else:
                reply = "📋 终检指令格式：\n`终检 订单号` - 提交终检任务"
            logger.info(f"[WeChatAppBot] 收到终检指令: {content}")
        elif content == '质检记录':
            reply = "📊 正在查询质检记录，请稍候..."
            logger.info(f"[WeChatAppBot] 收到查询质检记录指令")
        elif content.startswith('完工量') or content.startswith('实际完成'):
            parts = content.replace('完工量', '').replace('实际完成', '').strip().split()
            if len(parts) >= 2:
                qty = parts[-1]
                order_no = parts[0]
                process = ' '.join(parts[1:-1]) if len(parts) > 2 else ''
                try:
                    wechat_server_url = os.environ.get('WECHAT_SERVER_URL', 'http://127.0.0.1:5003')
                    api_url = f"{wechat_server_url}/api/sync/report/actual"
                    resp = requests.post(api_url, json={
                        'order_no': order_no,
                        'process': process,
                        'actual_qty': int(qty),
                        'operator': user_id
                    }, timeout=10)
                    result = resp.json()
                    if result.get('code') == 200:
                        reply = f"✅ 实际完成量填报成功！\n订单: {order_no}\n工序: {process or '—'}\n实际完成量: {qty}"
                    else:
                        reply = f"❌ 填报失败：{result.get('message', '未知错误')}"
                except Exception as e:
                    reply = f"❌ 填报失败：网络错误 {e}"
                    logger.error(f"[WeChatAppBot] 完工量填报异常: {e}")
            else:
                reply = "📋 完工量指令格式：\n`完工量 订单号 工序 数量`\n例：完工量 WO0001 编织 150\n或：`实际完成 WO0001 编织 150`"
            logger.info(f"[WeChatAppBot] 收到完工量指令: {content}")
        elif content in ['查群成员', '查询群成员', '成员', '群成员']:
            logger.info(f"[WeChatAppBot] 收到查询群成员指令 from {user_id}, chat={chat_id}")
            if not chat_id:
                reply = "❌ 查群成员需要在群聊中使用，请在群聊里发送此指令。"
            else:
                group_data = self.get_group_member_list(chat_id)
                if group_data is None:
                    reply = "❌ 无法获取群成员列表，可能无权限或群ID无效。"
                else:
                    members = group_data.get('member_list', [])
                    if not members:
                        reply = "📋 群里暂无成员。"
                    else:
                        lines = [f"👥 群成员列表（共 {len(members)} 人）："]
                        for i, m in enumerate(members[:30], 1):
                            name = m.get('name', m.get('userid', '未知'))
                            type_label = "外部" if m.get('type') == 1 else "内部"
                            join_time = m.get('join_time', '')
                            lines.append(f"{i}. {name} [{type_label}]")
                        if len(members) > 30:
                            lines.append(f"...还有 {len(members) - 30} 人")
                        reply = '\n'.join(lines)
        else:
            reply = (
                f"您好，您的消息已收到，但我没有识别到有效指令。\n\n"
                f"🤖 您可以尝试以下指令：\n"
                f"📝 `报工 订单号 工序 数量` - 提交报工\n"
                f"🔍 `查询 订单号` - 查询订单\n"
                f"📋 `任务` - 查看我的任务\n"
                f"📦 `领料 订单号 物品 数量` - 领料申请\n"
                f"🔧 `报修 种类 事项` - 设备报修\n"
                f"✅ `质检 订单号` - 提交质检任务\n"
                f"👥 `查群成员` - 查看群成员列表\n"
                f"❓ `帮助` - 查看完整帮助"
            )
            logger.info(f"[WeChatAppBot] 未识别指令: {content}")

        if user_id:
            self.send_text_to_user(user_id, reply)
            logger.info(f"[WeChatAppBot] 已回复用户 {user_id}")

        return 'success'

    def _build_help_text(self) -> str:
        """构建帮助文本"""
        return (
            "🤖 **生产任务助手 - 使用帮助**\n\n"
            "📝 **报工**\n"
            "`报工 订单号 工序 数量 [完成]`\n"
            "例：报工 ORD202604001 编织 200\n\n"
            "📦 **领料**\n"
            "`领料 订单号 物品 规格 数量`\n"
            "例：领料 ORD202604001 不锈钢丝 2.0mm 50\n\n"
            "🔧 **报修**\n"
            "`报修 种类 事项`\n"
            "例：报修 设备故障 编织机异响\n\n"
            "🔍 **查询**\n"
            "`查询 订单号` 或 `查单 订单号`\n\n"
            "📋 **任务**\n"
            "`任务` / `我的任务` / `待办`\n\n"
            "✅ **确认**\n"
            "`确认 任务ID` 或 `收到`\n\n"
            "🧪 **质检**\n"
            "`质检 订单号` - 提交质检任务\n"
            "`首检 订单号` - 提交首检任务\n"
            "`巡检 订单号` - 提交巡检任务\n"
            "`终检 订单号` - 提交终检任务\n"
            "`质检记录` - 查看质检记录\n\n"
            "📊 **完工量**\n"
            "`完工量 订单号 工序 数量` - 填报实际完成量\n"
            "`实际完成 订单号 工序 数量` - 同上\n\n"
            "❌ **取消**\n"
            "`取消 任务ID`\n\n"
            "👥 **查群成员**\n"
            "`查群成员` / `客户`\n\n"
            "❓ **帮助**\n"
            "`帮助` / `help` / `?`"
        )

# 全局应用机器人实例
wechat_app_bot = None

def init_app_bot(corp_id, agent_id, secret):
    """初始化企业微信应用机器人"""
    global wechat_app_bot
    if corp_id and agent_id and secret:
        wechat_app_bot = WeChatAppBot(corp_id, agent_id, secret)
        logger.info("企业微信应用机器人已初始化")
        return wechat_app_bot
    return None

def get_app_bot():
    """获取应用机器人实例"""
    return wechat_app_bot

def send_task_notification(task_data, chat_id=None, user_id=None):
    """发送任务通知"""
    if not wechat_app_bot:
        logger.warning("应用机器人未配置")
        return False
    
    from template_engine import _render_template
    content = _render_template('tmpl_task_assigned', {
        '订单号': task_data.get('order_no', '未知'),
        '工序': task_data.get('process', '未知'),
        '数量': task_data.get('planned_qty', 0),
    })
    
    if chat_id:
        return wechat_app_bot.send_text_to_group(chat_id, content)
    elif user_id:
        return wechat_app_bot.send_text_to_user(user_id, content)
    return False

# 消息加密/解密相关
def generate_signature(token, timestamp, nonce, encrypt):
    """生成签名"""
    params = [token, timestamp, nonce, encrypt]
    params.sort()
    return hashlib.sha1(''.join(params).encode()).hexdigest()

def check_signature(token, signature, timestamp, nonce, encrypt):
    """验证签名"""
    expected = generate_signature(token, timestamp, nonce, encrypt)
    return expected == signature
