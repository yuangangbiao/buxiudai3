# -*- coding: utf-8 -*-
"""
通知服务模块

统一管理企业微信通知
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from dotenv import load_dotenv
from template_engine import _render_template, _send_wechat_message

logger = logging.getLogger(__name__)


class WeChatNotifier:
    """
    企业微信通知服务

    统一管理所有企业微信通知，包括：
    - 新任务通知
    - 任务分配通知
    - 任务完成通知
    - 库存预警通知
    - 自定义通知
    """

    def __init__(self):
        load_dotenv()

        self._enabled = os.getenv('ENABLE_WECHAT_NOTIFY', 'true').lower() == 'true'
        self._notify_task_assigned = os.getenv('NOTIFY_ON_TASK_ASSIGNED', 'true').lower() == 'true'
        self._notify_task_completed = os.getenv('NOTIFY_ON_TASK_COMPLETED', 'true').lower() == 'true'
        self._notify_low_stock = os.getenv('NOTIFY_ON_LOW_STOCK', 'false').lower() == 'true'

        self._message_hub = None
        self._container_center = None

    def initialize(self, message_hub=None, container_center=None):
        """
        初始化通知服务

        Args:
            message_hub: 消息中心实例
            container_center: 容器中心实例
        """
        from bots.message_hub import get_hub

        self._message_hub = message_hub or get_hub()
        self._container_center = container_center

        logger.info(f"[WeChatNotifier] 初始化完成，enabled={self._enabled}")

    @property
    def enabled(self) -> bool:
        """是否启用通知"""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        """设置是否启用通知"""
        self._enabled = value

    def notify_new_task(self, task_data: Dict[str, Any]) -> bool:
        """
        通知新任务

        Args:
            task_data: 任务数据，包含:
                - task_id: 任务ID
                - order_no: 订单号
                - process: 工序
                - planned_qty: 计划数量
                - operator_id: 操作员ID（可选）

        Returns:
            bool: 发送是否成功
        """
        if not self._enabled:
            logger.debug("[WeChatNotifier] 通知已禁用")
            return False

        if not self._message_hub:
            logger.warning("[WeChatNotifier] 消息中心未初始化")
            return False

        order_no = task_data.get('order_no', '未知')
        process = task_data.get('process', '未知')
        planned_qty = task_data.get('planned_qty', 0)
        task_id = task_data.get('task_id', '')
        operator_id = task_data.get('operator_id', '')

        content = _render_template('tmpl_task_assigned', {
            '操作员': task_data.get('operator_id', ''),
            '任务标题': process,
            '订单号': order_no,
            '工序': process,
            '数量': planned_qty,
        })

        try:
            success = self._message_hub.broadcast(content)
            if success:
                logger.info(f"[WeChatNotifier] 新任务通知发送成功: {task_id}")
            else:
                logger.warning(f"[WeChatNotifier] 新任务通知发送失败: {task_id}")
            return success
        except Exception as e:
            logger.error(f"[WeChatNotifier] 发送新任务通知异常: {e}")
            return False

    def notify_task_assigned(self, task_data: Dict[str, Any], operator_id: str) -> bool:
        """
        通知任务分配

        Args:
            task_data: 任务数据
            operator_id: 被分配的操作员ID

        Returns:
            bool: 发送是否成功
        """
        if not self._enabled or not self._notify_task_assigned:
            return False

        if not self._message_hub:
            logger.warning("[WeChatNotifier] 消息中心未初始化")
            return False

        order_no = task_data.get('order_no', '未知')
        process = task_data.get('process', '未知')
        planned_qty = task_data.get('planned_qty', 0)
        task_id = task_data.get('task_id', '')

        content = _render_template('tmpl_task_assigned', {
            '操作员': operator_id,
            '任务标题': process,
            '订单号': order_no,
            '工序': process,
            '数量': planned_qty,
        })

        try:
            success = self._message_hub.send_to_user(operator_id, content)
            if success:
                logger.info(f"[WeChatNotifier] 任务分配通知发送成功: {task_id} -> {operator_id}")
            else:
                logger.warning(f"[WeChatNotifier] 任务分配通知发送失败: {task_id} -> {operator_id}")
            return success
        except Exception as e:
            logger.error(f"[WeChatNotifier] 发送任务分配通知异常: {e}")
            return False

    def notify_task_completed(self, task_data: Dict[str, Any]) -> bool:
        """
        通知任务完成

        Args:
            task_data: 任务数据，包含:
                - task_id: 任务ID
                - order_no: 订单号
                - process: 工序
                - completed_qty: 完成数量

        Returns:
            bool: 发送是否成功
        """
        if not self._enabled or not self._notify_task_completed:
            return False

        if not self._message_hub:
            logger.warning("[WeChatNotifier] 消息中心未初始化")
            return False

        order_no = task_data.get('order_no', '未知')
        process = task_data.get('process', '未知')
        completed_qty = task_data.get('completed_qty', 0)
        task_id = task_data.get('task_id', '')

        content = _render_template('tmpl_task_completed', {
            '操作员': task_data.get('operator_id', ''),
            '任务标题': process,
            '订单号': order_no,
            '数量': completed_qty,
        })

        try:
            success = self._message_hub.broadcast(content)
            if success:
                logger.info(f"[WeChatNotifier] 任务完成通知发送成功: {task_id}")
            else:
                logger.warning(f"[WeChatNotifier] 任务完成通知发送失败: {task_id}")
            return success
        except Exception as e:
            logger.error(f"[WeChatNotifier] 发送任务完成通知异常: {e}")
            return False

    def notify_low_stock(self, material_data: Dict[str, Any]) -> bool:
        """
        通知库存预警

        Args:
            material_data: 物料数据，包含:
                - material_name: 物料名称
                - current_stock: 当前库存
                - min_stock: 最低库存/缺货量
                - unit: 单位
                - daily_consumption: 日均消耗（可选）

        Returns:
            bool: 发送是否成功
        """
        if not self._enabled or not self._notify_low_stock:
            return False

        material_name = material_data.get('material_name', '未知')
        current_stock = material_data.get('current_stock', 0)
        min_stock = material_data.get('min_stock', material_data.get('shortage', 0))
        unit = material_data.get('unit', '')
        daily_consumption = material_data.get('daily_consumption', 0)

        # 计算可用天数
        if daily_consumption and daily_consumption > 0:
            available_days = int(current_stock / daily_consumption)
        else:
            available_days = '未知'

        content = _render_template('tmpl_material_lowstock', {
            '物料名称': material_name,
            '当前库存': current_stock,
            '单位': unit,
            '安全库存': min_stock,
            '可用天数': available_days,
        })

        try:
            ok, err = _send_wechat_message(content, 'markdown')
            if ok:
                logger.info(f"[WeChatNotifier] 库存预警通知发送成功: {material_name}")
            else:
                logger.warning(f"[WeChatNotifier] 库存预警通知发送失败: {material_name} err={err}")
            return ok
        except Exception as e:
            logger.error(f"[WeChatNotifier] 发送库存预警通知异常: {e}")
            return False

    def notify_custom(self, title: str, content: str, target: str = None,
                     bot_type: str = 'group') -> bool:
        """
        发送自定义通知

        Args:
            title: 通知标题
            content: 通知内容
            target: 目标（用户ID或群ID），None表示广播
            bot_type: 机器人类型 ('group' 或 'app')

        Returns:
            bool: 发送是否成功
        """
        if not self._enabled:
            return False

        if not self._message_hub:
            logger.warning("[WeChatNotifier] 消息中心未初始化")
            return False

        full_content = f"**{title}**\n\n{content}"

        try:
            if target:
                from bots.base import BotType
                bt = BotType.APP if bot_type == 'app' else BotType.GROUP
                success = self._message_hub.send_to_user(target, full_content, bot_type=bt)
            else:
                success = self._message_hub.broadcast(full_content)

            if success:
                logger.info(f"[WeChatNotifier] 自定义通知发送成功: {title}")
            else:
                logger.warning(f"[WeChatNotifier] 自定义通知发送失败: {title}")
            return success
        except Exception as e:
            logger.error(f"[WeChatNotifier] 发送自定义通知异常: {e}")
            return False

    def notify_report_submitted(self, report_data: Dict[str, Any]) -> bool:
        """
        通知报工提交

        Args:
            report_data: 报工数据，包含:
                - order_no: 订单号
                - process: 工序
                - quantity: 数量
                - operator: 操作员

        Returns:
            bool: 发送是否成功
        """
        if not self._enabled:
            return False

        order_no = report_data.get('order_no', '未知')
        process = report_data.get('process', '未知')
        quantity = report_data.get('quantity', 0)
        operator = report_data.get('operator', '未知')

        content = _render_template('tmpl_report_submitted', {
            '订单号': order_no,
            '工序': process,
            '数量': quantity,
            '操作员': operator,
        })

        try:
            success = self._message_hub.broadcast(content)
            return success
        except Exception as e:
            logger.error(f"[WeChatNotifier] 发送报工提交通知异常: {e}")
            return False

    def get_info(self) -> Dict[str, Any]:
        """获取通知服务信息"""
        return {
            'enabled': self._enabled,
            'notify_task_assigned': self._notify_task_assigned,
            'notify_task_completed': self._notify_task_completed,
            'notify_low_stock': self._notify_low_stock,
            'message_hub_initialized': self._message_hub is not None,
        }


_notifier_instance: Optional[WeChatNotifier] = None


def get_notifier() -> WeChatNotifier:
    """
    获取通知服务单例

    Returns:
        WeChatNotifier: 通知服务实例
    """
    global _notifier_instance
    if _notifier_instance is None:
        _notifier_instance = WeChatNotifier()
        _notifier_instance.initialize()
    return _notifier_instance
