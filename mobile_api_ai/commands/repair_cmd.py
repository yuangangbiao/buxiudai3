# -*- coding: utf-8 -*-
"""
报修指令模块

处理报修相关的用户指令
"""

import re
import json
import os
from typing import Optional, Dict, Any

from commands.base import (
    BaseCommand, ParsedCommand, CommandResult,
    CommandType, normalize_text
)

from container_config import container_config


class RepairCommand(BaseCommand):
    """
    报修指令

    支持格式：
    1. 报修 设备故障 机器卡死了
    2. 报修 R01 机器卡死了
    3. 报修 设备故障
    4. 报修 R01
    5. 报设备故障
    6. 设备故障
    """

    def __init__(self):
        super().__init__(
            name='报修',
            aliases=['报修', '报设备', '报故障', '维修', '修', '故障', '设备']
        )

    def get_patterns(self) -> list:
        repair_keywords = '报修|报设备|报故障|维修|修|故障|设备'
        
        return [
            # 格式: 报修 种类ID 描述 (如 报修 R01 机器卡死)
            rf'^(?:{repair_keywords})\s+(R\d{{2}})\s+(.+)',
            # 格式: 报修 种类名称 描述 (如 报修 设备故障 机器卡死)
            rf'^(?:{repair_keywords})\s+([\u4e00-\u9fff]+)\s+(.+)',
            # 格式: 报修 种类ID (最简)
            rf'^(?:{repair_keywords})\s+(R\d{{2}})$',
            # 格式: 报修 种类名称 (最简)
            rf'^(?:{repair_keywords})\s+([\u4e00-\u9fff]+)$',
            # 格式: 直接说种类名称 (如 设备故障)
            r'^(设备故障|电气维修|安全风险|空调故障)$',
        ]

    def _get_category_by_name(self, name: str) -> Optional[Dict]:
        """根据名称获取报修种类"""
        categories = container_config.get_all_repair_categories()
        for cat in categories:
            if cat.name == name or name in cat.name:
                return {
                    'id': cat.id,
                    'name': cat.name,
                    'icon': cat.icon,
                    'assigned_operator_id': cat.assigned_operator_id,
                    'description': cat.description
                }
        return None

    def _get_category_by_id(self, cat_id: str) -> Optional[Dict]:
        """根据ID获取报修种类"""
        cat = container_config.get_repair_category(cat_id)
        if cat:
            return {
                'id': cat.id,
                'name': cat.name,
                'icon': cat.icon,
                'assigned_operator_id': cat.assigned_operator_id,
                'description': cat.description
            }
        return None

    def parse(self, text: str) -> Optional[ParsedCommand]:
        """
        解析报修指令

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

                category_id = None
                category_name = None
                description = ''

                if group_count == 1:
                    val = groups[0]
                    if val.startswith('R') and len(val) == 3:
                        # 种类ID
                        category_id = val
                    else:
                        # 种类名称
                        category_name = val

                elif group_count == 2:
                    first = groups[0]
                    second = groups[1]
                    if first.startswith('R') and len(first) == 3:
                        category_id = first
                        description = second
                    else:
                        category_name = first
                        description = second

                # 根据名称获取ID
                if category_name and not category_id:
                    cat_info = self._get_category_by_name(category_name)
                    if cat_info:
                        category_id = cat_info['id']
                        category_name = cat_info['name']

                # 如果都没找到，尝试匹配关键词
                if not category_id:
                    keywords = {
                        '设备': 'R01',
                        '故障': 'R01',
                        '电气': 'R02',
                        '电': 'R02',
                        '安全': 'R03',
                        '风险': 'R03',
                        '空调': 'R04',
                    }
                    for kw, cat_id in keywords.items():
                        if kw in text:
                            category_id = cat_id
                            cat_info = self._get_category_by_id(category_id)
                            if cat_info:
                                category_name = cat_info['name']
                            break

                if not category_id:
                    continue

                return ParsedCommand(
                    command_type=CommandType.REPAIR,
                    raw_text=text,
                    args={
                        'category_id': category_id,
                        'category_name': category_name,
                        'description': description.strip(),
                    },
                    aliases=[self.name] + self.aliases
                )

        return None

    def execute(self, parsed: ParsedCommand, context: Dict) -> CommandResult:
        """
        执行报修指令

        Args:
            parsed: 解析后的指令
            context: 执行上下文，包含:
                - container_center: 容器中心实例
                - user_id: 用户ID

        Returns:
            CommandResult: 执行结果
        """
        category_id = parsed.args.get('category_id')
        category_name = parsed.args.get('category_name')
        description = parsed.args.get('description', '')

        container_center = context.get('container_center')
        user_id = context.get('user_id', 'unknown')

        if not container_center:
            return CommandResult.fail(
                message="系统错误：容器中心未初始化",
                error="Container center not available"
            )

        # 获取报修种类信息
        cat_info = self._get_category_by_id(category_id)
        if not cat_info:
            cat_info = {'name': category_name or '未知种类', 'assigned_operator_id': '', 'icon': '🔧'}

        try:
            # 创建报修任务
            content = {
                'category_id': category_id,
                'category_name': cat_info['name'],
                'description': description if description else '无详细描述',
                'reporter_id': user_id,
            }

            pkg = container_center.collect_repair(
                category_id=category_id,
                category_name=cat_info['name'],
                description=content['description'],
                reporter_id=user_id,
                target_operator=cat_info['assigned_operator_id']
            )

            # 派发任务
            container_center.distributor.distribute(pkg.id)

            icon = cat_info.get('icon', '🔧')
            message = f"{icon} **报修请求已提交！**\n\n"
            message += f"类型: {cat_info['name']}\n"
            if description:
                message += f"描述: {description}\n"
            message += f"报修人: {user_id}\n"
            message += f"任务ID: {pkg.id}\n\n"
            message += "已通知维修负责人处理"

            return CommandResult.ok(
                message=message,
                data={
                    'task_id': pkg.id,
                    'category_id': category_id,
                    'category_name': cat_info['name'],
                    'description': description,
                    'reporter_id': user_id,
                    'target_operator': cat_info['assigned_operator_id'],
                    'status': 'pending'
                }
            )

        except Exception as e:
            return CommandResult.fail(
                message=f"报修失败：{str(e)}",
                error=str(e)
            )

    def get_help(self) -> str:
        """获取帮助信息"""
        categories = container_config.get_all_repair_categories()
        cat_list = []
        for cat in categories:
            cat_list.append(f"{cat.icon} {cat.name} (ID: {cat.id})")

        return f"""**报修指令：**

📝 **报修格式**
`报修 设备故障 机器卡死了`
`报修 R01 机器卡死了`
`报修 设备故障`
`设备故障`

🔧 **报修种类**
{chr(10).join(cat_list)}

💡 **示例**
`报修 设备故障 编织机不转了` → 提交设备故障报修
`报修 电气维修 线路短路`     → 提交电气维修报修
`安全风险 地上有油污`          → 提交安全隐患上报"""
