# -*- coding: utf-8 -*-
"""
维修完成指令模块

处理维修完成上报和维修单号查询相关的用户指令
支持：
1. 维修完成上报（无描述时提示上报维修过程）
2. 维修补充（后期补充维修原因）
3. 维修单号查询
"""

import re
import time
from typing import Optional, Dict, Any

from commands.base import (
    BaseCommand, ParsedCommand, CommandResult,
    CommandType, normalize_text
)


class RepairCompleteCommand(BaseCommand):
    """
    维修完成指令

    支持格式：
    1. 维修完成 R202605001          → 提交完成，提示上报维修过程
    2. 维修完成 R202605001 已修复   → 提交完成并记录维修说明
    3. 维修补充 R202605001 更换零件 → 后期补充维修原因
    4. 查询维修 R202605001          → 查询维修单状态
    """

    def __init__(self):
        super().__init__(
            name='维修完成',
            aliases=['维修完成', '修完', '维修完工', '完工', '完成维修', '维修结束']
        )
        # 记录待补充维修原因的工单（用于定时问询）
        self.pending_repair_notes = {}

    def get_patterns(self) -> list:
        complete_keywords = '维修完成|修完|维修完工|完工|完成维修|维修结束'
        supplement_keywords = '维修补充|补充维修|补维修|修补充'
        query_keywords = '查询维修|查维修|维修查询|查修'
        
        return [
            # 格式: 维修补充 单号 描述 (如 维修补充 R202605001 更换零件)
            rf'^(?:{supplement_keywords})\s+(R?\d{{4,12}})\s+(.+)',
            # 格式: 维修补充 单号 (最简，支持4位后四位匹配)
            rf'^(?:{supplement_keywords})\s+(R?\d{{4,12}})$',
            # 格式: 维修完成 单号 描述 (如 维修完成 R202605001 已修复)
            rf'^(?:{complete_keywords})\s+(R?\d{{4,12}})\s+(.+)',
            # 格式: 维修完成 单号 (最简，支持4位后四位匹配)
            rf'^(?:{complete_keywords})\s+(R?\d{{4,12}})$',
            # 格式: 查询维修 单号 (支持4位后四位匹配)
            rf'^(?:{query_keywords})\s+(R?\d{{4,12}})$',
        ]

    def parse(self, text: str) -> Optional[ParsedCommand]:
        """
        解析维修完成/补充/查询指令

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

                repair_no = None
                description = ''
                command_action = 'complete'

                # 判断指令类型
                if any(kw in text for kw in ['维修补充', '补充维修', '补维修', '修补充']):
                    command_action = 'supplement'
                elif any(kw in text for kw in ['查询维修', '查维修', '维修查询', '查修']):
                    command_action = 'query'

                if group_count >= 1:
                    repair_no = groups[0]
                    # 如果单号没有前缀R且长度大于4位，自动加上R前缀
                    # 4位数字不添加前缀，作为后四位模糊匹配使用
                    if repair_no and not repair_no.startswith('R') and len(repair_no) > 4:
                        repair_no = 'R' + repair_no

                if group_count >= 2:
                    description = groups[1]

                if not repair_no:
                    continue

                return ParsedCommand(
                    command_type=CommandType.REPAIR_COMPLETE,
                    raw_text=text,
                    args={
                        'repair_no': repair_no,
                        'description': description.strip(),
                        'action': command_action,
                    },
                    aliases=[self.name] + self.aliases
                )

        return None

    def _find_repair_by_number(self, container_center, repair_no: str) -> Optional[Dict]:
        """
        根据维修单号查找维修记录（支持模糊匹配）

        支持的匹配方式：
        1. 精确匹配完整单号
        2. 去掉前缀R后的匹配
        3. 后四位模糊匹配（输入4位数字时）
        4. 通用模糊匹配

        Args:
            container_center: 容器中心实例
            repair_no: 维修单号

        Returns:
            Dict: 维修记录信息
        """
        try:
            # 先精确匹配
            result = container_center.query_repair(repair_no=repair_no)
            if result:
                return result

            # 如果精确匹配不到，尝试模糊匹配（去掉前缀R）
            if repair_no.startswith('R'):
                fuzzy_no = repair_no[1:]
                result = container_center.query_repair(fuzzy_no=fuzzy_no)
                if result:
                    return result

            # 如果输入是4位数字，尝试后四位匹配
            clean_no = repair_no.lstrip('R')
            if len(clean_no) == 4 and clean_no.isdigit():
                result = container_center.query_repair(suffix_match=clean_no)
                if result:
                    return result

            # 尝试更宽松的模糊匹配
            result = container_center.query_repair(fuzzy_no=repair_no)
            if result:
                return result

            # 如果去掉前缀R后是4位数字，再次尝试后四位匹配
            if repair_no.startswith('R') and len(repair_no) == 5 and repair_no[1:].isdigit():
                result = container_center.query_repair(suffix_match=repair_no[1:])
                if result:
                    return result

            return None
        except Exception as e:
            return None

    def _schedule_reminder(self, repair_no: str, user_id: str):
        """
        安排定时问询提醒

        Args:
            repair_no: 维修单号
            user_id: 用户ID
        """
        # 记录待补充的工单（实际项目中可使用定时任务调度）
        self.pending_repair_notes[repair_no] = {
            'user_id': user_id,
            'created_at': time.time(),
            'reminder_count': 0
        }

    def _clear_reminder(self, repair_no: str):
        """
        清除定时问询提醒

        Args:
            repair_no: 维修单号
        """
        if repair_no in self.pending_repair_notes:
            del self.pending_repair_notes[repair_no]

    def execute(self, parsed: ParsedCommand, context: Dict) -> CommandResult:
        """
        执行维修完成/补充/查询指令

        Args:
            parsed: 解析后的指令
            context: 执行上下文，包含:
                - container_center: 容器中心实例
                - user_id: 用户ID

        Returns:
            CommandResult: 执行结果
        """
        repair_no = parsed.args.get('repair_no')
        description = parsed.args.get('description', '')
        action = parsed.args.get('action', 'complete')

        container_center = context.get('container_center')
        user_id = context.get('user_id', 'unknown')

        if not container_center:
            return CommandResult.fail(
                message="系统错误：容器中心未初始化",
                error="Container center not available"
            )

        if action == 'query':
            # 查询维修记录
            repair_info = self._find_repair_by_number(container_center, repair_no)
            if not repair_info:
                return CommandResult.fail(
                    message=f"未找到维修单号: {repair_no}",
                    error="Repair not found"
                )

            # 格式化维修信息
            status_map = {
                'pending': '待处理',
                'processing': '维修中',
                'completed': '已完成',
                'cancelled': '已取消',
                'pending_note': '待补充维修说明'
            }

            message = f"🔧 **维修单查询结果**\n\n"
            message += f"单号: {repair_info.get('repair_no', repair_no)}\n"
            message += f"状态: {status_map.get(repair_info.get('status'), repair_info.get('status'))}\n"
            message += f"类型: {repair_info.get('category_name', '未知')}\n"
            message += f"报修人: {repair_info.get('reporter_id', '未知')}\n"
            if repair_info.get('repairer_id'):
                message += f"维修人: {repair_info.get('repairer_id')}\n"
            message += f"报修时间: {repair_info.get('created_at', '未知')}\n"
            if repair_info.get('description'):
                message += f"问题描述: {repair_info.get('description')}\n"
            if repair_info.get('repair_note'):
                message += f"维修说明: {repair_info.get('repair_note')}\n"
            else:
                message += f"维修说明: 待补充\n"
            if repair_info.get('completed_at'):
                message += f"完成时间: {repair_info.get('completed_at')}"

            return CommandResult.ok(
                message=message,
                data=repair_info
            )

        elif action == 'supplement':
            # 维修补充 - 后期补充维修原因
            if not description:
                return CommandResult.fail(
                    message="请补充维修原因，格式：维修补充 单号 维修原因",
                    error="Missing repair note"
                )

            repair_info = self._find_repair_by_number(container_center, repair_no)
            if not repair_info:
                return CommandResult.fail(
                    message=f"未找到维修单号: {repair_no}",
                    error="Repair not found"
                )

            try:
                # 更新维修说明
                result = container_center.supplement_repair(
                    repair_no=repair_no,
                    repair_note=description,
                    operator_id=user_id
                )

                if result:
                    # 清除定时提醒
                    self._clear_reminder(repair_no)

                    message = f"✅ **维修补充成功！**\n\n"
                    message += f"单号: {repair_no}\n"
                    message += f"维修说明: {description}\n"
                    message += "\n已更新维修数据库"

                    return CommandResult.ok(
                        message=message,
                        data={
                            'repair_no': repair_no,
                            'repair_note': description,
                            'operator_id': user_id
                        }
                    )
                else:
                    return CommandResult.fail(
                        message=f"维修补充失败，请重试",
                        error="Supplement repair failed"
                    )

            except Exception as e:
                return CommandResult.fail(
                    message=f"维修补充失败：{str(e)}",
                    error=str(e)
                )

        else:
            # 维修完成上报
            repair_info = self._find_repair_by_number(container_center, repair_no)
            if not repair_info:
                return CommandResult.fail(
                    message=f"未找到维修单号: {repair_no}",
                    error="Repair not found"
                )

            try:
                if description:
                    # 有维修说明，直接完成
                    result = container_center.complete_repair(
                        repair_no=repair_no,
                        repairer_id=user_id,
                        repair_note=description
                    )

                    if result:
                        message = f"✅ **维修完成！**\n\n"
                        message += f"单号: {repair_no}\n"
                        message += f"维修人: {user_id}\n"
                        message += f"维修情况: {description}\n"
                        message += "\n已计入维修数据库"

                        return CommandResult.ok(
                            message=message,
                            data={
                                'repair_no': repair_no,
                                'repairer_id': user_id,
                                'repair_note': description,
                                'status': 'completed'
                            }
                        )
                    else:
                        return CommandResult.fail(
                            message=f"维修完成失败，请重试",
                            error="Complete repair failed"
                        )
                else:
                    # 无维修说明，提交完成状态但要求补充维修过程
                    result = container_center.complete_repair(
                        repair_no=repair_no,
                        repairer_id=user_id,
                        repair_note='',
                        status='pending_note'  # 待补充状态
                    )

                    if result:
                        # 安排定时问询提醒
                        self._schedule_reminder(repair_no, user_id)

                        message = f"✅ **维修完成已提交！**\n\n"
                        message += f"单号: {repair_no}\n"
                        message += f"维修人: {user_id}\n\n"
                        message += "📝 请上报维修过程，格式：\n"
                        message += "`维修补充 R202605001 更换零件`\n\n"
                        message += "（如未补充，系统将定时发送问询）"

                        return CommandResult.ok(
                            message=message,
                            data={
                                'repair_no': repair_no,
                                'repairer_id': user_id,
                                'status': 'pending_note',
                                'need_note': True
                            }
                        )
                    else:
                        return CommandResult.fail(
                            message=f"维修完成失败，请重试",
                            error="Complete repair failed"
                        )

            except Exception as e:
                return CommandResult.fail(
                    message=f"维修完成失败：{str(e)}",
                    error=str(e)
                )

    def get_help(self) -> str:
        """获取帮助信息"""
        return f"""**维修指令：**

📝 **指令格式**
`维修完成 R202605001`              → 提交完成（需补充维修过程）
`维修完成 R202605001 更换零件`     → 提交完成并记录维修说明
`维修补充 R202605001 更换零件`     → 后期补充维修原因
`查询维修 R202605001`              → 查询维修单状态

🔧 **功能说明**
- 维修完成上报后如未说明维修原因，系统将定时发送问询
- 支持维修单号缩写模糊比对（如输入2605001可匹配R202605001）
- 维修原因支持后期补充，系统自动归类到对应工单
- 维修说明支持长输入描述

💡 **示例**
`维修完成 R202605001`           → 提交完成，提示补充维修过程
`维修完成 R202605001 更换电机`   → 完成维修并记录说明
`维修补充 R202605001 更换电机`   → 补充维修原因
`查询维修 R202605001`            → 查询维修单状态"""
