# -*- coding: utf-8 -*-
"""
报工指令模块

处理报工相关的用户指令
"""

import re
from typing import Optional, Dict, Any

from commands.base import (
    BaseCommand, ParsedCommand, CommandResult,
    CommandType, normalize_text
)

from report_request_manager import get_report_request_manager


class ReportCommand(BaseCommand):
    """
    报工指令

    支持格式（从复杂到简单）：
    1. 报工 WO0001 编织 50      → 完整格式
    2. 报 1 编织 50            → 后4位有效数字，自动匹配 WO0001
    3. 报 1 50                → 自动获取工序
    4. 报 1                   → 最简报工
    5. WO0001                 → 直接发送订单号
    6. 1                      → 纯数字，只输后4位有效数字
    """

    def __init__(self):
        super().__init__(
            name='报工',
            aliases=['报工', '报', '完工', '完成', 'report', 'b', 'bg', '检验', '检', '质检', 'qc']
        )

    def get_patterns(self) -> list:
        # 报工关键词
        report_keywords = '报工|报|完工|完成|b|bg'
        # 检验关键词
        qc_keywords = '检验|检|质检|qc'

        return [
            # 完整格式: 报工/检验 订单号 工序 数量 [完成]
            rf'^(?:{report_keywords}|{qc_keywords})\s+(WO\d+)\s+(\S+)\s+(\d+)',
            # 格式: 报工/检验 后4位数字+工单 工序 数量 (如 报 0001工单 编织 200)
            rf'^(?:{report_keywords}|{qc_keywords})\s+(\d{{1,4}})工单\s+(\S+)\s+(\d+)',
            # 格式: 报工/检验 后4位数字 工序 数量 [完成] (有空格)
            rf'^(?:{report_keywords}|{qc_keywords})\s+(\d{{1,4}})\s+(\S+)\s+(\d+)',
            # 连续格式: 报工/检验 W+数字+工序+数量 (如 报W1编织200, 报W4148编织200)
            rf'^(?:{report_keywords}|{qc_keywords})(W\d+)([\u4e00-\u9fff]+)(\d+)',
            # 连续格式: 报工/检验 W+数字+数量 (如 报W1200)
            rf'^(?:{report_keywords}|{qc_keywords})(W\d+)(\d{{3,4}})$',
            # 连续格式: 报工/检验 后4位数字+工序+数量 (无空格，如 报4148编织200)
            rf'^(?:{report_keywords}|{qc_keywords})(\d{{4}})([\u4e00-\u9fff]+)(\d+)',
            # 连续格式: 报工/检验 后4位数字+数量 (无空格，如 报4148200)
            rf'^(?:{report_keywords}|{qc_keywords})(\d{{4}})(\d{{3}})$',
            # 格式: 报工/检验 订单号 数量
            rf'^(?:{report_keywords}|{qc_keywords})\s+(WO\d+)\s+(\d+)',
            # 格式: 报工/检验 后4位数字 数量 (有空格)
            rf'^(?:{report_keywords}|{qc_keywords})\s+(\d{{1,4}})\s+(\d+)',
            # 格式: 报工/检验 订单号 (最简)
            rf'^(?:{report_keywords}|{qc_keywords})\s+(WO\d+)',
            # 格式: 报工/检验 后4位数字 (最简)
            rf'^(?:{report_keywords}|{qc_keywords})\s+(\d{{1,4}})',
            # 格式: 直接发送订单号
            r'^(WO\d+)$',
            # 格式: 直接发送纯数字（后4位有效数字）
            r'^(\d{1,4})$',
        ]

    def parse(self, text: str) -> Optional[ParsedCommand]:
        """
        解析报工指令

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
                group_count = len(groups)

                # 默认值
                order_no = None
                short_suffix = None
                process = None
                quantity = 100

                if group_count == 1:
                    # 直接发送订单号或纯数字
                    val = groups[0]
                    if val.upper().startswith('WO'):
                        order_no = val.upper()
                    elif val.isdigit():
                        short_suffix = str(int(val))

                elif group_count == 2:
                    # 格式: (数字/订单号, 数量) 如 报4148200 或 报W1200
                    first = groups[0]
                    second = groups[1]
                    if first.isdigit() and second.isdigit():
                        # 工单后4位 + 数量
                        short_suffix = first
                        quantity = int(second)
                    elif second.isdigit():
                        # 订单号/前缀 + 数量
                        if first.upper().startswith('W'):
                            order_no = first.upper()
                            quantity = int(second)
                        elif first.isdigit():
                            short_suffix = first
                            quantity = int(second)

                elif group_count == 3:
                    first = groups[0]
                    second = groups[1]
                    third = groups[2]

                    # 处理 W 前缀开头的情况
                    if first.upper().startswith('W') and third.isdigit() and not second.isdigit():
                        # 格式: (W订单号, 工序, 数量) 如 报W1编织200
                        order_no = first.upper()
                        process = second
                        quantity = int(third)
                    elif first.isdigit() and third.isdigit() and not second.isdigit():
                        # 格式: (4位数字, 工序, 数量) 如 报4148编织200
                        short_suffix = first
                        process = second
                        quantity = int(third)
                    elif first.isdigit() and second.isdigit():
                        # 格式: (4位数字, 数量) 如 报4148200
                        short_suffix = first
                        quantity = int(second)
                    elif third.isdigit():
                        quantity = int(third)
                        if second.isdigit():
                            short_suffix = str(int(second))
                        elif second.upper().startswith('W'):
                            order_no = second.upper()
                        else:
                            process = second
                            if first.isdigit():
                                short_suffix = str(int(first))
                    else:
                        process = third
                        if second.isdigit():
                            short_suffix = str(int(second))
                        elif second.upper().startswith('W'):
                            order_no = second.upper()

                elif group_count == 4:
                    cmd = groups[0]
                    second = groups[1]
                    process = groups[2]
                    quantity = int(groups[3])
                    if second.isdigit():
                        short_suffix = str(int(second))
                    elif second.upper().startswith('WO'):
                        order_no = second.upper()

                # 报工关键词
                report_keywords = ['报工', '报', '完工', '完成', 'b', 'bg']
                # 检验关键词
                qc_keywords = ['检验', '检', '质检', 'qc']

                # 检测任务类型
                first_word = groups[0] if groups else ''
                if first_word in qc_keywords:
                    task_type = 'qc'  # 质检任务
                else:
                    task_type = 'report'  # 报工任务

                is_completed = any(kw in text for kw in ['完成', '完工', '好', '结束', 'completed', 'done'])

                return ParsedCommand(
                    command_type=CommandType.REPORT,
                    raw_text=text,
                    args={
                        'order_no': order_no,
                        'short_suffix': short_suffix,
                        'process': process,
                        'quantity': quantity,
                        'completed': is_completed,
                        'task_type': task_type,  # 区分报工/质检
                    },
                    aliases=[self.name] + self.aliases
                )

        return None

    def execute(self, parsed: ParsedCommand, context: Dict) -> CommandResult:
        """
        执行报工指令

        Args:
            parsed: 解析后的指令
            context: 执行上下文，包含:
                - container_center: 容器中心实例
                - operator_id: 操作员ID
                - bot: 机器人实例

        Returns:
            CommandResult: 执行结果
        """
        order_no = parsed.args.get('order_no')
        short_suffix = parsed.args.get('short_suffix')
        process = parsed.args.get('process')
        quantity = parsed.args.get('quantity')
        is_completed = parsed.args.get('completed', False)
        task_type = parsed.args.get('task_type', 'report')  # 默认为报工

        task_type_name = "质检" if task_type == 'qc' else "报工"

        container_center = context.get('container_center')

        if not container_center:
            return CommandResult.fail(
                message="系统错误：容器中心未初始化",
                error="Container center not available"
            )

        try:
            # 检查容器中心是否有报工方法
            if not hasattr(container_center, 'get_task_by_order'):
                return CommandResult.fail(
                    message="系统暂不支持报工功能",
                    error="Method not available"
                )

            # 如果只输入了两位数字，查找匹配的订单
            if short_suffix:
                all_tasks = container_center.get_all_tasks(limit=100)
                matched_task = None
                for t in all_tasks:
                    related_order = t.get('related_order', '')
                    if related_order.endswith(short_suffix):
                        matched_task = t
                        break

                if matched_task:
                    order_no = matched_task.get('related_order')
                    task = matched_task
                else:
                    return CommandResult.fail(
                        message=f"未找到尾号为 {short_suffix} 的订单任务",
                        error="Task not found"
                    )
            else:
                # 先尝试精确匹配
                task = container_center.get_task_by_order(order_no)

                # 如果没找到，尝试前缀/后缀匹配
                if not task and order_no:
                    all_tasks = container_center.get_all_tasks(limit=500)
                    order_upper = order_no.upper()

                    # 优先精确前缀匹配
                    for t in all_tasks:
                        related = t.get('related_order', '').upper()
                        if related.startswith(order_upper):
                            task = t
                            order_no = t.get('related_order')
                            break

                    # 如果还没找到，尝试后缀匹配
                    if not task:
                        for t in all_tasks:
                            related = t.get('related_order', '').upper()
                            if related.endswith(order_upper):
                                task = t
                                order_no = t.get('related_order')
                                break

            if not task:
                return CommandResult.fail(
                    message=f"未找到订单 {order_no} 的任务",
                    error="Task not found"
                )

            task_id = task.get('id')

            if not process:
                process = task.get('process_name') or task.get('content', {}).get('process_name', '未知工序')

            # 获取任务信息
            planned_qty = task.get('content', {}).get('planned_qty', 0)
            current_completed = task.get('completed_qty', 0)
            new_completed = current_completed + quantity
            remaining = max(0, planned_qty - new_completed)

            # 创建报工请求记录
            req_manager = get_report_request_manager()
            report_req = req_manager.create_request(
                order_no=order_no,
                process=process,
                quantity=quantity,
                operator=context.get('operator_id', 'unknown'),
                task_id=task_id,
                current_completed=current_completed,
                planned_qty=planned_qty,
                new_completed=new_completed,
                remaining=remaining
            )

            # 构造回调数据发送给主软件
            callback_data = {
                'request_id': report_req.id,
                'order_no': order_no,
                'process': process,
                'quantity': quantity,
                'operator': context.get('operator_id', 'unknown'),
                'task_id': task_id,
                'current_completed': current_completed,
                'planned_qty': planned_qty,
                'new_completed': new_completed,
                'remaining': remaining,
                'timestamp': report_req.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }

            # 记录到上下文，供后续处理
            context['report_request'] = callback_data

            # 返回待确认消息
            message = f"📝 报工请求已提交！\n\n订单号: {order_no}\n工序: {process}\n报工数量: {quantity}\n\n正在等待主软件确认..."

            return CommandResult.ok(
                message=message,
                data={
                    'order_no': order_no,
                    'process': process,
                    'quantity': quantity,
                    'request_id': report_req.id,
                    'status': 'pending',
                    'callback_data': callback_data
                }
            )

        except Exception as e:
            return CommandResult.fail(
                message=f"报工失败：{str(e)}",
                error=str(e)
            )

    def get_help(self) -> str:
        return """**生产报工/质检指令：**

📋 **报工任务**（生产车间报工）
报 1       → 最简单，自动匹配 WO0001
报 10 50   → 匹配 WO0010 + 报50件
报 WO0001 50 → 完整格式

🔍 **质检任务**（质检员检验）
检 1       → 最简单，自动匹配 WO0001
检 10 50   → 匹配 WO0010 + 检50件
检 WO0001 50 → 完整格式

📋 **完整格式**
`报 WO0001 编织 200`
`检 WO0001 外观 100`

📝 **后4位有效数字自动去除前导零**
`1`   → WO0001
`10`  → WO0010
`100` → WO0100"""
