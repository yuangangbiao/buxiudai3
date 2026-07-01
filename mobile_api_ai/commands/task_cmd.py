# -*- coding: utf-8 -*-
"""
任务指令模块

处理任务相关的用户指令
"""

import re
from typing import Optional, Dict

from commands.base import (
    BaseCommand, ParsedCommand, CommandResult,
    CommandType, normalize_text
)


class TaskCommand(BaseCommand):
    """
    任务指令

    支持格式：
    - 任务
    - 我的任务
    - 待办
    - task
    """

    STATUS_MAP = {
        'pending': '⏳ 待处理',
        'assigned': '📋 已分配',
        'in_progress': '🔄 进行中',
        'completed': '✅ 已完成',
        'cancelled': '❌ 已取消',
    }

    def __init__(self):
        super().__init__(
            name='任务',
            aliases=['任务', 'task', 'tasks', '待办', '我的任务']
        )

    def parse(self, text: str) -> Optional[ParsedCommand]:
        """
        解析任务指令

        Args:
            text: 用户输入

        Returns:
            ParsedCommand: 解析后的指令
        """
        text = normalize_text(text)
        text_lower = text.lower().strip()

        task_keywords = ['任务', 'task', 'tasks', '待办', '我的任务']

        for keyword in task_keywords:
            if text_lower == keyword or text_lower.startswith(keyword):
                return ParsedCommand(
                    command_type=CommandType.TASK,
                    raw_text=text,
                    args={
                        'include_completed': '已完成' in text or 'completed' in text_lower,
                    },
                    aliases=[self.name] + self.aliases
                )

        return None

    def execute(self, parsed: ParsedCommand, context: Dict) -> CommandResult:
        """
        执行任务指令

        Args:
            parsed: 解析后的指令
            context: 执行上下文

        Returns:
            CommandResult: 执行结果
        """
        operator_id = context.get('operator_id')
        include_completed = parsed.args.get('include_completed', False)

        container_center = context.get('container_center')

        if not container_center:
            return CommandResult.fail(
                message="系统错误：容器中心未初始化",
                error="Container center not available"
            )

        try:
            # 检查容器中心是否有任务查询方法
            if not hasattr(container_center, 'get_tasks_by_operator'):
                return CommandResult.fail(
                    message="系统暂不支持任务查询功能",
                    error="Method not available"
                )

            tasks = container_center.get_tasks_by_operator(operator_id)

            if not include_completed:
                tasks = [t for t in tasks if t.get('status') != 'completed']

            if not tasks:
                return CommandResult.ok(
                    message="✅ 当前没有待处理的任务",
                    data={'tasks': []}
                )

            task_list = []
            message_lines = ["**📋 您的任务列表：**\n"]

            for i, task in enumerate(tasks[:10], 1):
                task_id = task.get('task_id', '')
                order_no = task.get('order_no', '')
                process = task.get('process', '')
                status = task.get('status', 'unknown')
                planned_qty = task.get('planned_qty', 0)
                completed_qty = task.get('completed_qty', 0)

                status_text = self.STATUS_MAP.get(status, status)

                message_lines.append(
                    f"{i}. {status_text} {order_no} - {process}\n"
                    f"   数量：{completed_qty}/{planned_qty}"
                )

                task_list.append({
                    'task_id': task_id,
                    'order_no': order_no,
                    'process': process,
                    'status': status,
                    'planned_qty': planned_qty,
                    'completed_qty': completed_qty,
                })

            if len(tasks) > 10:
                message_lines.append(f"\n... 还有 {len(tasks) - 10} 个任务")

            message = '\n'.join(message_lines)

            return CommandResult.ok(
                message=message,
                data={
                    'tasks': task_list,
                    'total': len(tasks),
                }
            )

        except Exception as e:
            return CommandResult.fail(
                message=f"获取任务列表失败：{str(e)}",
                error=str(e)
            )

    def get_help(self) -> str:
        return "任务指令：任务 / 我的任务 / 待办\n" \
               "显示您的待处理任务列表"
