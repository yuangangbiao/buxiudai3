# -*- coding: utf-8 -*-
"""
查询指令模块

处理查询相关的用户指令
"""

import re
from typing import Optional, Dict

from commands.base import (
    BaseCommand, ParsedCommand, CommandResult,
    CommandType, normalize_text
)


class QueryCommand(BaseCommand):
    """
    查询指令

    支持格式：
    - 查询 订单号
    - 查询 ORD202604001
    - q ORD202604001
    """

    def __init__(self):
        super().__init__(
            name='查询',
            aliases=['查询', '查', 'q', 'query', '找', '搜']
        )

    def get_patterns(self) -> list:
        return [
            r'^(?:查询|查|q|query|找|搜)\s*(WO\d+)',
            r'^(?:查询|查|q|query|找|搜)\s*(\S+)',
            r'^(?:查询|查|q|query|找|搜)\s*(.+)',
            r'^(WO\d+)$',
            r'^(W0)$',
            r'^(\S+)$',
        ]

    def parse(self, text: str) -> Optional[ParsedCommand]:
        """
        解析查询指令

        Args:
            text: 用户输入

        Returns:
            ParsedCommand: 解析后的指令
        """
        text = normalize_text(text)

        patterns = self.get_patterns()

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()

                order_no = None
                short_suffix = None

                if len(groups) == 1:
                    # 单个值的情况
                    val = groups[0]
                    val_upper = val.upper()

                    if val_upper == 'W0':
                        # W0 查询所有进行中的任务
                        return ParsedCommand(
                            command_type=CommandType.QUERY,
                            raw_text=text,
                            args={'query_all': True},
                            aliases=self.aliases
                        )
                    elif val_upper.startswith('WO'):
                        order_no = val_upper
                    elif val.isdigit():
                        short_suffix = str(int(val))
                    elif len(val) <= 3:
                        # 短字符串，可能是前缀匹配（如 'w' -> 'WO'）
                        short_suffix = val_upper
                    else:
                        # 太长或无效，当作订单号处理
                        order_no = val_upper
                else:
                    # 有两个组的情况 (关键词 + 值)
                    keyword = groups[0]
                    value = groups[1]
                    value_upper = value.upper()

                    if value_upper.startswith('WO'):
                        order_no = value_upper
                    elif value.isdigit():
                        short_suffix = str(int(value))
                    elif len(value) <= 3:
                        # 短字符串，可能是前缀匹配
                        short_suffix = value_upper
                    else:
                        order_no = value_upper

                return ParsedCommand(
                    command_type=CommandType.QUERY,
                    raw_text=text,
                    args={
                        'order_no': order_no,
                        'short_suffix': short_suffix,
                    },
                    aliases=self.aliases
                )

        return None

    def execute(self, parsed: ParsedCommand, context: Dict) -> CommandResult:
        """
        执行查询指令

        Args:
            parsed: 解析后的指令
            context: 执行上下文

        Returns:
            CommandResult: 执行结果
        """
        order_no = parsed.args.get('order_no')
        short_suffix = parsed.args.get('short_suffix')
        query_all = parsed.args.get('query_all', False)

        container_center = context.get('container_center')

        if not container_center:
            return CommandResult.fail(
                message="系统错误：容器中心未初始化",
                error="Container center not available"
            )

        try:
            # 检查容器中心是否有查询方法
            if not hasattr(container_center, 'get_tasks_by_order'):
                return CommandResult.fail(
                    message="系统暂不支持查询功能",
                    error="Method not available"
                )

            completed_statuses = ('completed', 'cancelled', 'expired')

            # W0 查询所有进行中的任务
            if query_all:
                all_tasks = container_center.get_all_tasks(limit=500)
                tasks = [t for t in all_tasks if t.get('status') not in completed_statuses]
                search_key = "W0"

                if not tasks:
                    return CommandResult.ok(
                        message="✅ 目前没有进行中的任务，全部完成！",
                        data={'order_no': search_key, 'tasks': []}
                    )
            elif short_suffix:
                all_tasks = container_center.get_all_tasks(limit=500)
                matched_tasks = []
                exact_matches = []

                # 精确匹配（订单号以short_suffix结尾，且之前是字母或开始）
                for t in all_tasks:
                    related_order = t.get('related_order', '')
                    if related_order.endswith(short_suffix):
                        # 检查是否是精确匹配（如 1 匹配 1，但 11 不应该被 1 匹配）
                        # 精确匹配：结尾就是short_suffix，前面应该是字母或数字较少
                        if len(related_order) == len(short_suffix) or related_order[:-len(short_suffix)].isdigit() == False:
                            matched_tasks.append(t)
                        # 完全相等
                        if related_order == short_suffix or related_order.upper() == short_suffix.upper():
                            exact_matches.append(t)

                # 优先返回精确匹配
                if exact_matches:
                    tasks = exact_matches
                elif matched_tasks:
                    tasks = matched_tasks
                else:
                    # 如果后缀匹配数量太少，尝试前缀匹配
                    tasks = []
                    if len(short_suffix) <= 4:
                        short_suffix_upper = short_suffix.upper()
                        for t in all_tasks:
                            related_order = t.get('related_order', '').upper()
                            if related_order.startswith(short_suffix_upper):
                                tasks.append(t)
                # 判断是数字后缀还是字母前缀
                if short_suffix.isdigit():
                    search_key = f"#{short_suffix}"
                else:
                    search_key = f"#{short_suffix}*"

                # 过滤已完成的任务
                tasks = [t for t in tasks if t.get('status') not in completed_statuses]
            else:
                tasks = container_center.get_tasks_by_order(order_no)
                search_key = order_no
                tasks = [t for t in tasks if t.get('status') not in completed_statuses]

            if not tasks:
                return CommandResult.ok(
                    message=f"未找到工单 {search_key} 的任务",
                    data={'order_no': search_key, 'tasks': []}
                )

            task_list = []
            for task in tasks:
                content = task.get('content', {})
                task_list.append({
                    'task_id': task.get('id', ''),
                    'order_no': task.get('related_order', ''),
                    'process': content.get('process_name', '') or task.get('related_process', ''),
                    'status': task.get('status', ''),
                    'planned_qty': content.get('planned_qty', 0) or 0,
                    'completed_qty': task.get('completed_qty', 0) or 0,
                })

            # 按订单号分组
            orders = {}
            for t in task_list:
                order = t['order_no']
                if order not in orders:
                    orders[order] = []
                orders[order].append(t)

            message_lines = [f"**{search_key} 的任务（共{len(orders)}个工单）：**\n"]

            # 只显示前5个工单
            for order, order_tasks in list(orders.items())[:5]:
                message_lines.append(f"\n📋 {order}：")
                for t in order_tasks[:5]:  # 每个工单最多5个工序
                    status_emoji = {
                        'pending': '⏳',
                        'assigned': '📋',
                        'in_progress': '🔄',
                        'completed': '✅',
                        'cancelled': '❌',
                    }.get(t['status'], '❓')

                    completed = t['completed_qty']
                    planned = t['planned_qty']
                    progress = int(completed / planned * 10) if planned > 0 else 0
                    bar = '█' * progress + '░' * (10 - progress)

                    message_lines.append(
                        f"  {status_emoji} {t['process']}: {completed}/{planned} {bar}"
                    )

                if len(order_tasks) > 5:
                    message_lines.append(f"  ... 还有{len(order_tasks) - 5}个工序")

            if len(orders) > 5:
                message_lines.append(f"\n... 还有{len(orders) - 5}个工单")

            message = '\n'.join(message_lines)

            return CommandResult.ok(
                message=message,
                data={
                    'order_no': search_key,
                    'tasks': task_list,
                }
            )

        except Exception as e:
            return CommandResult.fail(
                message=f"查询失败：{str(e)}",
                error=str(e)
            )

    def get_help(self) -> str:
        return """**查询指令：**

🔍 **查询工单状态**
`查 1`      → 查询后4位为1的工单
`查 10`     → 查询后4位为10的工单
`查 WO0001` → 查询完整订单号
`查 ORD...` → 查询完整订单号

📊 **返回信息**
订单号、工序、完成进度、剩余数量"""
