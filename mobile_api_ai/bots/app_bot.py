# -*- coding: utf-8 -*-
"""
应用机器人实现模块

基于企业微信应用机器人的 API 方式
支持发送消息给指定用户或外部群
"""

import os
import requests
import time
import threading
from typing import List, Dict, Any, Optional
import logging

from bots.base import BaseBot
from circuit_breaker_integration import circuit_protected
from fault_tolerance import fault_tolerance

logger = logging.getLogger(__name__)


class AppBot(BaseBot):
    """
    企业微信应用机器人

    使用企业微信应用 API 发送消息
    支持：
    - 发送消息给指定用户
    - 发送消息到外部群
    - 获取用户信息
    """

    API_BASE = 'https://qyapi.weixin.qq.com/cgi-bin'
    TOKEN_EXPIRE_BUFFER = 300

    def __init__(self, corp_id: str, agent_id: str, secret: str):
        """
        初始化应用机器人

        Args:
            corp_id: 企业ID
            agent_id: 应用AgentID
            secret: 应用Secret
        """
        super().__init__()
        self.corp_id = corp_id
        self.agent_id = agent_id
        self.secret = secret
        self.name = 'AppBot'

        self._access_token = None
        self._token_expire_time = 0
        self._token_lock = threading.Lock()

    @circuit_protected("appbot_token")
    def _refresh_token(self) -> bool:
        """
        刷新 access_token

        Returns:
            bool: 刷新是否成功
        """
        with self._token_lock:
            now = int(time.time())

            if self._access_token and now < self._token_expire_time:
                return True

            url = f"{self.API_BASE}/gettoken?corpid={self.corp_id}&corpsecret={self.secret}"

            try:
                resp = fault_tolerance.execute_with_retry(lambda: requests.get(url, timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10'))))
                result = resp.json()

                if result.get('errcode') == 0:
                    self._access_token = result['access_token']
                    expires_in = result.get('expires_in', 7200)
                    self._token_expire_time = now + expires_in - self.TOKEN_EXPIRE_BUFFER
                    logger.info("[AppBot] Token刷新成功")
                    return True
                else:
                    logger.error(f"[AppBot] Token刷新失败: {result}")
                    return False

            except requests.exceptions.RequestException as e:
                logger.error(f"[AppBot] Token请求异常: {e}")
                return False
            except Exception as e:
                logger.error(f"[AppBot] Token刷新异常: {e}")
                return False

    def get_access_token(self) -> Optional[str]:
        """
        获取 access_token

        Returns:
            str: token 或 None
        """
        if self._refresh_token():
            return self._access_token
        return None

    @circuit_protected("appbot_send")
    def _send_message(self, payload: Dict) -> bool:
        """
        发送消息的内部方法

        Args:
            payload: 消息载荷

        Returns:
            bool: 发送是否成功
        """
        token = self.get_access_token()
        if not token:
            logger.error("[AppBot] 获取token失败，无法发送消息")
            return False

        url = f"{self.API_BASE}/message/send?access_token={token}"

        try:
            resp = fault_tolerance.execute_with_retry(lambda: requests.post(
                url,
                json=payload,
                timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10')),
                headers={'Content-Type': 'application/json'}
            ))
            result = resp.json()

            if result.get('errcode') == 0:
                logger.info("[AppBot] 消息发送成功")
                return True
            else:
                logger.error(f"[AppBot] 发送失败: {result}")
                return False

        except requests.exceptions.Timeout:
            logger.error("[AppBot] 发送超时")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"[AppBot] 请求异常: {e}")
            return False
        except Exception as e:
            logger.error(f"[AppBot] 发送异常: {e}")
            return False

    def send_text(self, content: str, **kwargs) -> bool:
        """
        发送文本消息

        Args:
            content: 文本内容
            **kwargs:
                - user_id: 用户ID (user01,user02)
                - party_id: 部门ID (1,2)
                - tag_id: 标签ID (1,2,3)
                - to_all: 发送给所有人 (True/False)

        Returns:
            bool: 发送是否成功
        """
        user_id = kwargs.get('user_id', '')
        party_id = kwargs.get('party_id', '')
        tag_id = kwargs.get('tag_id', '')
        to_all = kwargs.get('to_all', False)

        payload = {
            'msgtype': 'text',
            'agentid': self.agent_id,
            'text': {
                'content': content
            },
            'safe': 0
        }

        if to_all:
            payload['touser'] = '@all'
        elif user_id:
            payload['touser'] = user_id
        elif party_id:
            payload['toparty'] = party_id
        elif tag_id:
            payload['totag'] = tag_id
        else:
            logger.warning("[AppBot] 未指定发送目标")
            return False

        return self._send_message(payload)

    def send_text_to_user(self, user_id: str, content: str) -> bool:
        """
        发送文本消息给单个用户

        Args:
            user_id: 用户ID
            content: 文本内容

        Returns:
            bool: 发送是否成功
        """
        return self.send_text(content, user_id=user_id)

    @circuit_protected("appbot_group_send")
    def send_text_to_group(self, chat_id: str, content: str) -> bool:
        """
        发送文本消息到外部群

        注意：需要使用客户联系接口，且需要配置客户群

        Args:
            chat_id: 群ID
            content: 文本内容

        Returns:
            bool: 发送是否成功
        """
        token = self.get_access_token()
        if not token:
            return False

        url = f"{self.API_BASE}/externalcontact/send_msg?access_token={token}"

        payload = {
            'chatid': chat_id,
            'msgtype': 'text',
            'text': {
                'content': content
            }
        }

        try:
            resp = fault_tolerance.execute_with_retry(lambda: requests.post(
                url,
                json=payload,
                timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10')),
                headers={'Content-Type': 'application/json'}
            ))
            result = resp.json()

            if result.get('errcode') == 0:
                logger.info(f"[AppBot] 群消息发送成功 to={chat_id}")
                return True
            else:
                logger.error(f"[AppBot] 群消息发送失败: {result}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"[AppBot] 群消息请求异常: {e}")
            return False
        except Exception as e:
            logger.error(f"[AppBot] 群消息发送异常: {e}")
            return False

    def send_markdown(self, content: str, **kwargs) -> bool:
        """
        发送Markdown消息

        企业微信支持的Markdown有限，详见官方文档

        Args:
            content: Markdown内容
            **kwargs: 发送目标参数

        Returns:
            bool: 发送是否成功
        """
        user_id = kwargs.get('user_id', '')
        party_id = kwargs.get('party_id', '')
        to_all = kwargs.get('to_all', False)

        payload = {
            'msgtype': 'markdown',
            'agentid': self.agent_id,
            'markdown': {
                'content': content
            },
            'safe': 0
        }

        if to_all:
            payload['touser'] = '@all'
        elif user_id:
            payload['touser'] = user_id
        elif party_id:
            payload['toparty'] = party_id
        else:
            logger.warning("[AppBot] 未指定发送目标")
            return False

        return self._send_message(payload)

    def send_news(self, articles: List[Dict[str, Any]], **kwargs) -> bool:
        """
        发送图文消息

        Args:
            articles: 图文列表，每个元素包含:
                - title: 标题
                - description: 描述
                - url: 点击链接
                - picurl: 图片URL
            **kwargs: 发送目标参数

        Returns:
            bool: 发送是否成功
        """
        user_id = kwargs.get('user_id', '')
        party_id = kwargs.get('party_id', '')
        to_all = kwargs.get('to_all', False)

        payload = {
            'msgtype': 'news',
            'agentid': self.agent_id,
            'news': {
                'articles': []
            },
            'safe': 0
        }

        for article in articles[:8]:
            payload['news']['articles'].append({
                'title': article.get('title', '')[:64],
                'description': article.get('description', '')[:512],
                'url': article.get('url', ''),
                'picurl': article.get('picurl', '')
            })

        if to_all:
            payload['touser'] = '@all'
        elif user_id:
            payload['touser'] = user_id
        elif party_id:
            payload['toparty'] = party_id
        else:
            logger.warning("[AppBot] 未指定发送目标")
            return False

        return self._send_message(payload)

    def send_template_card(self, card_data: Dict, **kwargs) -> bool:
        """
        发送模板卡片消息

        Args:
            card_data: 卡片数据
                - card_type: 卡片类型 (text_notice, news_notice, etc)
                - source: 来源信息
                - action_menu: 菜单信息
                - task_id: 任务ID
                - main_title: 主标题
                - emphasis_content: 强调内容
                - quote_area: 引用区域
                - sub_title_text: 子标题
                - horizontal_content_list: 水平内容列表
                - jump_list: 跳转列表
            **kwargs: 发送目标参数

        Returns:
            bool: 发送是否成功
        """
        user_id = kwargs.get('user_id', '')
        party_id = kwargs.get('party_id', '')
        to_all = kwargs.get('to_all', False)

        payload = {
            'msgtype': 'template_card',
            'agentid': self.agent_id,
            'template_card': card_data,
            'safe': 0
        }

        if to_all:
            payload['touser'] = '@all'
        elif user_id:
            payload['touser'] = user_id
        elif party_id:
            payload['toparty'] = party_id
        else:
            logger.warning("[AppBot] 未指定发送目标")
            return False

        return self._send_message(payload)

    @circuit_protected("appbot_user_info")
    def get_user_info(self, user_id: str) -> Optional[Dict]:
        """
        获取用户信息

        Args:
            user_id: 用户ID

        Returns:
            Dict: 用户信息或None
        """
        token = self.get_access_token()
        if not token:
            return None

        url = f"{self.API_BASE}/user/get?access_token={token}&userid={user_id}"

        try:
            resp = fault_tolerance.execute_with_retry(lambda: requests.get(url, timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10'))))
            result = resp.json()

            if result.get('errcode') == 0:
                return result
            else:
                logger.error(f"[AppBot] 获取用户信息失败: {result}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"[AppBot] 获取用户信息请求异常: {e}")
            return None
        except Exception as e:
            logger.error(f"[AppBot] 获取用户信息异常: {e}")
            return None

    @circuit_protected("appbot_dept_users")
    def get_department_users(self, department_id: int, fetch_child: bool = True) -> List[str]:
        """
        获取部门成员

        Args:
            department_id: 部门ID
            fetch_child: 是否获取子部门成员

        Returns:
            List[str]: 用户ID列表
        """
        token = self.get_access_token()
        if not token:
            return []

        url = f"{self.API_BASE}/user/simplelist?access_token={token}&department_id={department_id}&fetch_child={1 if fetch_child else 0}"

        try:
            resp = fault_tolerance.execute_with_retry(lambda: requests.get(url, timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10'))))
            result = resp.json()

            if result.get('errcode') == 0:
                return [user['userid'] for user in result.get('userlist', [])]
            else:
                logger.error(f"[AppBot] 获取部门成员失败: {result}")
                return []

        except requests.exceptions.RequestException as e:
            logger.error(f"[AppBot] 获取部门成员请求异常: {e}")
            return []
        except Exception as e:
            logger.error(f"[AppBot] 获取部门成员异常: {e}")
            return []

    @circuit_protected("appbot_dept_list")
    def get_department_list(self) -> List[Dict]:
        """
        获取部门列表

        Returns:
            List[Dict]: 部门列表，每个部门包含 id, name, parentid 等
        """
        token = self.get_access_token()
        if not token:
            return []

        url = f"{self.API_BASE}/department/list?access_token={token}"

        try:
            resp = fault_tolerance.execute_with_retry(lambda: requests.get(url, timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10'))))
            result = resp.json()

            if result.get('errcode') == 0:
                return result.get('department', [])
            else:
                logger.error(f"[AppBot] 获取部门列表失败: {result}")
                return []

        except requests.exceptions.RequestException as e:
            logger.error(f"[AppBot] 获取部门列表请求异常: {e}")
            return []
        except Exception as e:
            logger.error(f"[AppBot] 获取部门列表异常: {e}")
            return []

    def get_all_users(self) -> List[Dict]:
        """
        获取所有用户（遍历所有部门）

        Returns:
            List[Dict]: 所有用户列表，包含用户详细信息
        """
        all_users = []
        departments = self.get_department_list()

        for dept in departments:
            dept_id = dept.get('id')
            if dept_id:
                user_ids = self.get_department_users(dept_id, fetch_child=True)
                for user_id in user_ids:
                    user_info = self.get_user_info(user_id)
                    if user_info:
                        user_info['department'] = dept.get('name', '')
                        all_users.append(user_info)

        return all_users

    def is_connected(self) -> bool:
        """
        检查机器人是否已连接

        Returns:
            bool: 是否已连接
        """
        return self._refresh_token()

    def get_info(self) -> Dict:
        """获取机器人信息"""
        return {
            'type': self.bot_type.value,
            'name': self.name,
            'connected': self.is_connected(),
            'corp_id': self.corp_id,
            'agent_id': self.agent_id,
        }
