# -*- coding: utf-8 -*-
"""
企业微信通知集成服务
容器中心通过此服务向企业微信群发送通知

@deprecated: 请使用 services/notifier.py 中的 WeChatNotifier 替代
             此版本保留供 container_center_v5.py 和 timeout_reminder.py 兼容使用
"""
import os
import requests
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import threading
import time

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)
logger.warning("[DEPRECATED] integration/wechat_notifier.py 已弃用，请迁移到 services/notifier.py")


class WeChatNotifier:
    """
    企业微信通知服务

    @deprecated: 请使用 services.notifier.WeChatNotifier 替代

    支持功能：
    - 任务分配通知
    - 任务完成通知
    - 订单进度通知
    - 质检结果通知
    """

    def __init__(self, webhook_url: str = None, container_center_url: str = None):
        logger.warning("[DEPRECATED] WeChatNotifier(integration) 已弃用，请使用 services.notifier.WeChatNotifier")
        self.webhook_url = webhook_url or os.getenv('WECHAT_WORK_BOT_URL', '')
        self.container_center_url = container_center_url or os.getenv('CONTAINER_CENTER_URL', 'http://localhost:5002')
        self.operator_mapping = {}  # 真实映射由企业架构动态提供，不再硬编码

    def send_notification(self, content: str) -> bool:
        """
        发送通知到企业微信群

        Args:
            content: 通知内容

        Returns:
            是否发送成功
        """
        if not self.webhook_url:
            logger.warning('[WeChatNotifier] 未配置企业微信Webhook URL')
            return False

        try:
            data = {
                'msgtype': 'text',
                'text': {'content': content}
            }
            response = requests.post(self.webhook_url, json=data, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
            result = response.json()
            if result.get('errcode') == 0:
                logger.info(f'[WeChatNotifier] 通知发送成功')
                return True
            else:
                logger.warning(f'[WeChatNotifier] 通知发送失败: {result.get("errmsg")}')
                return False
        except Exception as e:
            logger.error(f'[WeChatNotifier] 发送异常: {e}')
            return False

    def notify_task_assigned(self, task_id: str, operator_id: str,
                            task_title: str, related_order: str = None) -> bool:
        """
        通知任务已分配

        Args:
            task_id: 任务ID
            operator_id: 操作员ID
            task_title: 任务标题
            related_order: 关联订单号

        Returns:
            是否发送成功
        """
        operator_info = self.operator_mapping.get(operator_id, {'name': operator_id, 'wechat': operator_id})
        mention = operator_info['wechat']

        content = f"""
{mention} 您有新的任务！
━━━━━━━━━━━━━━━━━━━━
任务ID: {task_id}
任务: {task_title}
订单: {related_order or '-'}
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
━━━━━━━━━━━━━━━━━━━━
请确认收到任务：发送"确认"或"确认 {task_id}"
"""
        return self.send_notification(content)

    def notify_task_completed(self, task_id: str, operator_id: str,
                             task_title: str, result: str = None) -> bool:
        """
        通知任务已完成

        Args:
            task_id: 任务ID
            operator_id: 操作员ID
            task_title: 任务标题
            result: 完成结果

        Returns:
            是否发送成功
        """
        operator_info = self.operator_mapping.get(operator_id, {'name': operator_id, 'wechat': operator_id})

        content = f"""
[OK] 任务已完成！
━━━━━━━━━━━━━━━━━━━━
任务ID: {task_id}
任务: {task_title}
操作员: {operator_info['name']}
结果: {result or '成功'}
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
━━━━━━━━━━━━━━━━━━━━
"""
        return self.send_notification(content)

    def notify_quality_result(self, order_no: str, inspector_id: str,
                            result: str, issues: List[str] = None) -> bool:
        """
        通知质检结果

        Args:
            order_no: 订单号
            inspector_id: 质检员ID
            result: 质检结果 (合格/不合格/需复检)
            issues: 问题列表

        Returns:
            是否发送成功
        """
        inspector_info = self.operator_mapping.get(inspector_id, {'name': inspector_id, 'wechat': inspector_id})

        issue_lines = ''
        if issues:
            issue_lines = '\n'.join([f'  - {i}' for i in issues])
            issue_lines = f'\n问题:\n{issue_lines}'

        status_icon = '✅' if result == '合格' else ('⚠️' if result == '需复检' else '❌')

        content = f"""
{status_icon} 质检结果通知
━━━━━━━━━━━━━━━━━━━━
订单: {order_no}
质检员: {inspector_info['name']}
结果: {result}{issue_lines}
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
━━━━━━━━━━━━━━━━━━━━
"""
        return self.send_notification(content)

    def notify_order_progress(self, order_no: str, customer: str = None,
                            processes: List[Dict] = None) -> bool:
        """
        通知订单进度

        Args:
            order_no: 订单号
            customer: 客户名称
            processes: 工序进度列表

        Returns:
            是否发送成功
        """
        process_lines = ''
        if processes:
            for p in processes:
                icon = '✅' if p.get('status') == '已完成' else ('🔄' if p.get('status') == '进行中' else '⏳')
                process_lines += f'{icon} {p.get("name", "-")} - {p.get("status", "-")}\n'

        content = f"""
📋 订单进度
━━━━━━━━━━━━━━━━━━━━
订单: {order_no}
客户: {customer or '-'}
━━━━━━━━━━━━━━━━━━━━
{process_lines}
━━━━━━━━━━━━━━━━━━━━
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return self.send_notification(content)

    def notify_report_success(self, order_no: str, process_name: str,
                            quantity: int, operator_id: str) -> bool:
        """
        通知报工成功

        Args:
            order_no: 订单号
            process_name: 工序名称
            quantity: 数量
            operator_id: 操作员ID

        Returns:
            是否发送成功
        """
        operator_info = self.operator_mapping.get(operator_id, {'name': operator_id, 'wechat': operator_id})

        content = f"""
[OK] 报工成功！
━━━━━━━━━━━━━━━━━━━━
订单: {order_no}
工序: {process_name}
数量: {quantity}
操作员: {operator_info['name']}
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
━━━━━━━━━━━━━━━━━━━━
数据已同步到跟单系统！
"""
        return self.send_notification(content)

    def notify_system_status(self, status: str, details: str = None) -> bool:
        """
        通知系统状态

        Args:
            status: 状态
            details: 详情

        Returns:
            是否发送成功
        """
        content = f"""
[系统通知]
━━━━━━━━━━━━━━━━━━━━
状态: {status}
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
━━━━━━━━━━━━━━━━━━━━
{details or ''}
"""
        return self.send_notification(content)


class TaskPollingNotifier:
    """
    任务轮询通知器
    定期检查容器池，发现新任务时自动通知
    """

    def __init__(self, notifier: WeChatNotifier, poll_interval: int = 5):
        self.notifier = notifier
        self.poll_interval = poll_interval
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.last_notified_tasks = set()

    def start(self):
        """启动轮询"""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.thread.start()
        logger.info('[TaskPollingNotifier] 已启动')

    def stop(self):
        """停止轮询"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=int(os.environ.get('REQUEST_TIMEOUT_QUICK', '2')))
        logger.info('[TaskPollingNotifier] 已停止')

    def _poll_loop(self):
        """轮询循环"""
        while self.running:
            try:
                self._check_and_notify()
            except Exception as e:
                logger.error(f'[TaskPollingNotifier] 轮询异常: {e}')
            time.sleep(self.poll_interval)

    def _check_and_notify(self):
        """检查并通知"""
        try:
            response = requests.get(
                f'{self.notifier.container_center_url}/api/pool/tasks/pending',
                timeout=int(os.environ.get('REQUEST_TIMEOUT_QUICK', '3'))
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 0:
                    tasks = data.get('data', [])
                    for task in tasks:
                        task_id = task.get('id')
                        if task_id and task_id not in self.last_notified_tasks:
                            self._notify_new_task(task)
                            self.last_notified_tasks.add(task_id)
        except Exception as e:
            pass

    def _notify_new_task(self, task: Dict):
        """通知新任务"""
        task_id = task.get('id')
        operator_id = task.get('target_operator')
        title = task.get('title', '新任务')
        related_order = task.get('related_order')

        if operator_id:
            self.notifier.notify_task_assigned(
                task_id=task_id,
                operator_id=operator_id,
                task_title=title,
                related_order=related_order
            )


# 全局实例
wechat_notifier = WeChatNotifier()
