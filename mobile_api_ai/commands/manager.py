# -*- coding: utf-8 -*-
"""
指令管理器模块

管理和执行所有指令
"""

import re
import logging
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field

from commands.base import (
    BaseCommand, ParsedCommand, CommandResult,
    CommandType, normalize_text
)

logger = logging.getLogger(__name__)


@dataclass
class CommandRegistry:
    """指令注册表"""
    commands: Dict[str, BaseCommand] = field(default_factory=dict)
    type_handlers: Dict[CommandType, List[Callable]] = field(default_factory=dict)


class CommandManager:
    """
    指令管理器

    负责：
    - 注册和查找指令
    - 解析用户输入
    - 执行指令并返回结果
    """

    HELP_COMMANDS = ['help', '帮助', 'h', '？', '?']
    REPORT_COMMANDS = ['报工', 'report', 'report', '完工', '完成']
    QUERY_COMMANDS = ['查询', 'query', 'q', '搜', '找']
    TASK_COMMANDS = ['任务', 'task', 'tasks', '待办']
    CONFIRM_COMMANDS = ['确认', 'confirm', 'ok', '好的', '收到']
    COMPLETE_COMMANDS = ['完成', 'complete', 'done', '结束了']
    CANCEL_COMMANDS = ['取消', 'cancel', '撤销', '删除']

    def __init__(self):
        self._registry = CommandRegistry()
        self._default_handler: Optional[Callable] = None
        self._register_builtin_commands()

    def _register_builtin_commands(self):
        """注册内置指令"""
        from commands.report_cmd import ReportCommand
        from commands.query_cmd import QueryCommand
        from commands.task_cmd import TaskCommand
        from commands.help_cmd import HelpCommand
        from commands.outsource_cmd import OutsourcCommand
        from commands.repair_cmd import RepairCommand
        from commands.repair_complete_cmd import RepairCompleteCommand

        self.register(ReportCommand())
        self.register(QueryCommand())
        self.register(TaskCommand())
        self.register(HelpCommand())
        self.register(OutsourcCommand())
        self.register(RepairCommand())
        self.register(RepairCompleteCommand())

        logger.info("[CommandManager] 内置指令注册完成")

    def register(self, command: BaseCommand):
        """
        注册指令

        Args:
            command: 指令实例
        """
        self._registry.commands[command.name] = command

        for alias in command.aliases:
            self._registry.commands[alias] = command

        logger.debug(f"[CommandManager] 指令注册: {command.name}")

    def unregister(self, name: str):
        """
        注销指令

        Args:
            name: 指令名称
        """
        if name in self._registry.commands:
            cmd = self._registry.commands[name]
            del self._registry.commands[name]

            for alias in cmd.aliases:
                if alias in self._registry.commands:
                    del self._registry.commands[alias]

            logger.debug(f"[CommandManager] 指令注销: {name}")

    def get_command(self, name: str) -> Optional[BaseCommand]:
        """
        获取指令

        Args:
            name: 指令名称或别名

        Returns:
            BaseCommand: 指令实例
        """
        return self._registry.commands.get(name)

    def parse(self, text: str) -> ParsedCommand:
        """
        解析用户输入

        Args:
            text: 用户输入的文本

        Returns:
            ParsedCommand: 解析后的指令
        """
        text = normalize_text(text)

        for cmd_name, command in self._registry.commands.items():
            if command.matches(text):
                parsed = command.parse(text)
                if parsed:
                    return parsed

        return ParsedCommand(
            command_type=CommandType.UNKNOWN,
            raw_text=text,
            args={'original': text}
        )

    def execute(self, parsed: ParsedCommand, context: Dict) -> CommandResult:
        """
        执行指令

        Args:
            parsed: 解析后的指令
            context: 执行上下文

        Returns:
            CommandResult: 执行结果
        """
        if parsed.command_type == CommandType.UNKNOWN:
            return CommandResult.fail(
                message=f"无法识别的指令: {parsed.raw_text}",
                error="Unknown command"
            )

        command = self.get_command(parsed.command_type.value)
        if not command:
            return CommandResult.fail(
                message=f"指令处理器不存在: {parsed.command_type.value}",
                error="No handler"
            )

        try:
            if not command.validate(parsed):
                return CommandResult.fail(
                    message="参数验证失败",
                    error="Validation failed"
                )

            result = command.execute(parsed, context)

            for handler in self._registry.type_handlers.get(parsed.command_type, []):
                try:
                    handler(parsed, result, context)
                except Exception as e:
                    logger.error(f"[CommandManager] 后置处理器异常: {e}")

            return result

        except Exception as e:
            logger.error(f"[CommandManager] 指令执行异常: {e}")
            return CommandResult.fail(
                message=f"执行失败: {str(e)}",
                error=str(e)
            )

    def process(self, text: str, context: Dict) -> CommandResult:
        """
        处理用户输入（解析+执行）

        Args:
            text: 用户输入的文本
            context: 执行上下文

        Returns:
            CommandResult: 执行结果
        """
        parsed = self.parse(text)
        return self.execute(parsed, context)

    def set_default_handler(self, handler: Callable):
        """
        设置默认处理器（当无法识别指令时调用）

        Args:
            handler: 处理函数
        """
        self._default_handler = handler

    def register_type_handler(self, command_type: CommandType, handler: Callable):
        """
        注册类型处理器（在指令执行后调用）

        Args:
            command_type: 指令类型
            handler: 处理函数
        """
        if command_type not in self._registry.type_handlers:
            self._registry.type_handlers[command_type] = []
        self._registry.type_handlers[command_type].append(handler)

    def get_all_commands(self) -> List[Dict]:
        """
        获取所有指令信息

        Returns:
            List[Dict]: 指令信息列表
        """
        seen = set()
        result = []

        for cmd in self._registry.commands.values():
            if id(cmd) in seen:
                continue
            seen.add(id(cmd))

            result.append({
                'name': cmd.name,
                'aliases': cmd.aliases,
                'help': cmd.get_help(),
            })

        return result

    def get_command_list(self) -> str:
        """
        获取指令列表的帮助文本

        Returns:
            str: 帮助文本
        """
        commands = self.get_all_commands()

        lines = ["**支持的指令：**\n"]

        for cmd in sorted(commands, key=lambda x: x['name']):
            aliases = ', '.join(cmd['aliases']) if cmd['aliases'] else ''
            lines.append(f"- `{cmd['name']}` {aliases}")
            lines.append(f"  {cmd['help']}\n")

        return '\n'.join(lines)


_manager_instance = None


def get_command_manager() -> CommandManager:
    """
    获取指令管理器单例

    Returns:
        CommandManager: 指令管理器实例
    """
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = CommandManager()
    return _manager_instance
