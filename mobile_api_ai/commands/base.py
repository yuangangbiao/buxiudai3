# -*- coding: utf-8 -*-
"""
指令基类模块

定义指令的通用接口
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CommandType(Enum):
    """指令类型枚举"""
    REPORT = 'report'
    QUERY = 'query'
    TASK = 'task'
    OUTSOURCE = 'outsource'
    REPAIR = 'repair'
    REPAIR_COMPLETE = 'repair_complete'
    CONFIRM = 'confirm'
    COMPLETE = 'complete'
    CANCEL = 'cancel'
    HELP = 'help'
    UNKNOWN = 'unknown'


@dataclass
class ParsedCommand:
    """
    解析后的指令数据

    Attributes:
        command_type: 指令类型
        raw_text: 原始文本
        args: 解析出的参数
        aliases: 可能的指令别名
    """
    command_type: CommandType = CommandType.UNKNOWN
    raw_text: str = ''
    args: Dict[str, Any] = field(default_factory=dict)
    aliases: List[str] = field(default_factory=list)

    def __repr__(self):
        return f"ParsedCommand(type={self.command_type.value}, args={self.args})"


@dataclass
class CommandResult:
    """
    指令执行结果

    Attributes:
        success: 是否成功
        message: 结果消息
        data: 附加数据
        error: 错误信息
    """
    success: bool = False
    message: str = ''
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'success': self.success,
            'message': self.message,
            'data': self.data,
            'error': self.error,
        }

    @classmethod
    def ok(cls, message: str = '', data: Dict = None) -> 'CommandResult':
        """创建成功结果"""
        return cls(success=True, message=message, data=data or {})

    @classmethod
    def fail(cls, message: str = '', error: str = None) -> 'CommandResult':
        """创建失败结果"""
        return cls(success=False, message=message, error=error or message)


class BaseCommand(ABC):
    """
    指令基类

    所有具体指令都需要继承此类
    """

    def __init__(self, name: str, aliases: List[str] = None):
        """
        初始化指令

        Args:
            name: 指令名称
            aliases: 指令别名列表
        """
        self.name = name
        self.aliases = aliases or []
        self.logger = logging.getLogger(f"{__name__}.{name}")

    @abstractmethod
    def parse(self, text: str) -> Optional[ParsedCommand]:
        """
        解析文本

        Args:
            text: 用户输入的文本

        Returns:
            ParsedCommand: 解析后的指令，如果文本不匹配则返回None
        """
        pass

    @abstractmethod
    def execute(self, parsed: ParsedCommand, context: Dict) -> CommandResult:
        """
        执行指令

        Args:
            parsed: 解析后的指令
            context: 执行上下文，包含用户信息、机器人实例等

        Returns:
            CommandResult: 执行结果
        """
        pass

    def get_help(self) -> str:
        """
        获取指令帮助信息

        Returns:
            str: 帮助文本
        """
        return f"指令 {self.name} 的帮助信息"

    def validate(self, parsed: ParsedCommand) -> bool:
        """
        验证指令参数

        Args:
            parsed: 解析后的指令

        Returns:
            bool: 参数是否有效
        """
        return True

    def get_patterns(self) -> List[str]:
        """
        获取匹配模式列表

        Returns:
            List[str]: 正则表达式模式列表
        """
        return []

    def matches(self, text: str) -> bool:
        """
        检查文本是否匹配此指令

        Args:
            text: 用户输入的文本

        Returns:
            bool: 是否匹配
        """
        text_lower = text.lower().strip()

        if text_lower.startswith(self.name.lower()):
            return True

        for alias in self.aliases:
            if text_lower.startswith(alias.lower()):
                return True

        return False


def normalize_text(text: str) -> str:
    """
    规范化文本

    Args:
        text: 原始文本

    Returns:
        str: 规范化后的文本
    """
    text = text.strip()
    text = ' '.join(text.split())
    return text
