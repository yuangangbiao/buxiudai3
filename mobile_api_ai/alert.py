# -*- coding: utf-8 -*-
"""
告警通知模块 - 多渠道告警发送端

职责：向外部渠道（微信企业号、钉钉、邮件、日志）发送告警通知
与 container_center 告警模块的关系：
  - 本模块 = 告警发送端（对外推送）
  - container_center 告警模块 = 告警管理端（CRUD + 规则触发后台调度）
  - 两者互补，本模块不依赖 container_center

支持：
- 微信企业号
- 钉钉机器人
- 邮件通知
- 日志记录

使用方式：
    from alert import send_alert, AlertLevel

    send_alert("订单超时未处理", AlertLevel.WARNING, tags=['order', 'timeout'])
    send_alert("数据库连接失败", AlertLevel.CRITICAL, tags=['database'])
"""
import os
import smtplib
import logging
from typing import List, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from enum import Enum
from functools import wraps

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """告警级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AlertChannel(Enum):
    """通知渠道"""
    WECHAT_WORK = "wechat_work"
    DINGTALK = "dingtalk"
    EMAIL = "email"
    LOG = "log"


def _get_config():
    """获取告警配置"""
    return {
        'enabled': os.getenv('ALERT_ENABLED', 'true').lower() == 'true',
        'wechat_work': {
            'enabled': os.getenv('WECHAT_WORK_ALERT_ENABLED', 'false').lower() == 'true',
            'webhook': os.getenv('WECHAT_WORK_ALERT_WEBHOOK', ''),
        },
        'dingtalk': {
            'enabled': os.getenv('DINGTALK_ALERT_ENABLED', 'false').lower() == 'true',
            'webhook': os.getenv('DINGTALK_ALERT_WEBHOOK', ''),
            'secret': os.getenv('DINGTALK_ALERT_SECRET', ''),
        },
        'email': {
            'enabled': os.getenv('EMAIL_ALERT_ENABLED', 'false').lower() == 'true',
            'smtp_host': os.getenv('EMAIL_SMTP_HOST', 'smtp.gmail.com'),
            'smtp_port': int(os.getenv('EMAIL_SMTP_PORT', '587')),
            'smtp_user': os.getenv('EMAIL_SMTP_USER', ''),
            'smtp_password': os.getenv('EMAIL_SMTP_PASSWORD', ''),
            'from_addr': os.getenv('EMAIL_FROM', ''),
            'to_addrs': os.getenv('EMAIL_TO', '').split(','),
        }
    }


def _send_wechat_work(message: str, level: AlertLevel, tags: List[str]):
    """发送微信企业号告警"""
    config = _get_config()['wechat_work']
    if not config['enabled'] or not config['webhook']:
        return False

    try:
        import requests
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": f"### 🔔 {level.value} 告警\n"
                           f"**消息**: {message}\n\n"
                           f"**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                           f"**标签**: {' '.join([f'`{t}`' for t in tags])}\n\n"
                           f"**来源**: 不锈钢网带跟单系统"
            }
        }
        resp = requests.post(config['webhook'], json=payload, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        logger.error(f"[Alert] 微信企业号告警失败: {e}")
        return False


def _send_dingtalk(message: str, level: AlertLevel, tags: List[str]):
    """发送钉钉告警"""
    config = _get_config()['dingtalk']
    if not config['enabled'] or not config['webhook']:
        return False

    try:
        import requests
        import hmac
        import hashlib
        import base64
        import urllib.parse
        import time

        if config['secret']:
            timestamp = str(round(time.time() * 1000))
            secret_enc = config['secret'].encode('utf-8')
            string_to_sign = f'{timestamp}\n{config["secret"]}'
            string_to_sign_enc = string_to_sign.encode('utf-8')
            sign = base64.b64encode(hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()).decode('utf-8')
            sign = urllib.parse.quote_plus(sign)
            url = f"{config['webhook']}&timestamp={timestamp}&sign={sign}"
        else:
            url = config['webhook']

        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": f"{level.value} 告警",
                "text": f"### 🔔 {level.value} 告警\n\n"
                       f"> **消息**: {message}\n\n"
                       f"> **时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                       f"> **标签**: {' / '.join(tags)}\n\n"
                       f"> **来源**: 不锈钢网带跟单系统"
            }
        }
        resp = requests.post(url, json=payload, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        logger.error(f"[Alert] 钉钉告警失败: {e}")
        return False


def _send_email(message: str, level: AlertLevel, tags: List[str]):
    """发送邮件告警"""
    config = _get_config()['email']
    if not config['enabled'] or not config['smtp_user']:
        return False

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"[{level.value}] 不锈钢网带跟单系统告警"
        msg['From'] = config['from_addr']
        msg['To'] = ', '.join(config['to_addrs'])

        body = f"""
        <html>
        <body>
        <h2>🔔 {level.value} 告警</h2>
        <table>
            <tr><td><strong>消息</strong></td><td>{message}</td></tr>
            <tr><td><strong>时间</strong></td><td>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
            <tr><td><strong>标签</strong></td><td>{', '.join(tags)}</td></tr>
            <tr><td><strong>来源</strong></td><td>不锈钢网带跟单系统</td></tr>
        </table>
        </body>
        </html>
        """
        msg.attach(MIMEText(body, 'html'))

        with smtplib.SMTP(config['smtp_host'], config['smtp_port']) as server:
            server.starttls()
            server.login(config['smtp_user'], config['smtp_password'])
            server.send_message(msg)
        return True
    except Exception as e:
        logger.error(f"[Alert] 邮件告警失败: {e}")
        return False


def send_alert(
    message: str,
    level: AlertLevel = AlertLevel.INFO,
    tags: Optional[List[str]] = None,
    channels: Optional[List[AlertChannel]] = None,
    exception: Optional[Exception] = None
) -> bool:
    """
    发送告警

    Args:
        message: 告警消息
        level: 告警级别
        tags: 标签列表
        channels: 通知渠道（默认所有）
        exception: 关联的异常对象

    Returns:
        是否发送成功
    """
    config = _get_config()
    if not config['enabled']:
        return False

    tags = tags or []

    if exception:
        message += f"\n\n异常信息: {type(exception).__name__}: {str(exception)}"
        tags.append('exception')

    log_msg = f"[{level.value}] {message}"
    if tags:
        log_msg += f" [{'|'.join(tags)}]"

    if level == AlertLevel.CRITICAL:
        logger.critical(log_msg)
    elif level == AlertLevel.ERROR:
        logger.error(log_msg)
    elif level == AlertLevel.WARNING:
        logger.warning(log_msg)
    else:
        logger.info(log_msg)

    if channels is None:
        channels = [AlertChannel.LOG]

    success = False
    for channel in channels:
        if channel == AlertChannel.WECHAT_WORK:
            success = _send_wechat_work(message, level, tags) or success
        elif channel == AlertChannel.DINGTALK:
            success = _send_dingtalk(message, level, tags) or success
        elif channel == AlertChannel.EMAIL:
            success = _send_email(message, level, tags) or success

    return success


def alert_on_error(level: AlertLevel = AlertLevel.ERROR, tags: Optional[List[str]] = None):
    """装饰器：函数执行出错时自动告警"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                send_alert(
                    f"函数 {func.__name__} 执行失败",
                    level=level,
                    tags=tags or [func.__module__],
                    exception=e
                )
                raise
        return wrapper
    return decorator


def critical_alert(tags: Optional[List[str]] = None):
    """装饰器：标记为关键函数，出错必告警"""
    return alert_on_error(level=AlertLevel.CRITICAL, tags=tags)


class AlertManager:
    """告警管理器 - 聚合告警"""

    def __init__(self, name: str, level: AlertLevel = AlertLevel.WARNING):
        self.name = name
        self.level = level
        self._count = 0
        self._last_send_time = 0

    def record(self, message: str, tags: Optional[List[str]] = None):
        """记录事件"""
        self._count += 1
        tags = tags or []
        tags.insert(0, self.name)

        if self._count >= 10 or (datetime.now().timestamp() - self._last_send_time > 300):
            send_alert(f"{self.name} 累计 {self._count} 次告警: {message}", self.level, tags)
            self._count = 0
            self._last_send_time = datetime.now().timestamp()

    def reset(self):
        """重置计数器"""
        self._count = 0
