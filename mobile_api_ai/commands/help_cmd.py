# -*- coding: utf-8 -*-
"""
帮助指令模块

处理帮助相关的用户指令
"""

from typing import Optional, Dict

from commands.base import (
    BaseCommand, ParsedCommand, CommandResult,
    CommandType
)


class HelpCommand(BaseCommand):
    """
    帮助指令

    支持格式：
    - 帮助
    - help
    - ?
    """

    def __init__(self):
        super().__init__(
            name='帮助',
            aliases=['帮助', 'help', 'h', '？', '?']
        )

    def parse(self, text: str) -> Optional[ParsedCommand]:
        """
        解析帮助指令

        Args:
            text: 用户输入

        Returns:
            ParsedCommand: 解析后的指令
        """
        text_lower = text.lower().strip()

        help_keywords = ['帮助', 'help', 'h', '？', '?']

        for keyword in help_keywords:
            if text_lower == keyword:
                return ParsedCommand(
                    command_type=CommandType.HELP,
                    raw_text=text,
                    args={},
                    aliases=[self.name] + self.aliases
                )

        return None

    def execute(self, parsed: ParsedCommand, context: Dict) -> CommandResult:
        """
        执行帮助指令

        Args:
            parsed: 解析后的指令
            context: 执行上下文

        Returns:
            CommandResult: 执行结果
        """
        help_text = self._build_help_text(context)

        return CommandResult.ok(
            message=help_text,
            data={}
        )

    def _build_help_text(self, context: Dict) -> str:
        """
        构建帮助文本

        Args:
            context: 执行上下文

        Returns:
            str: 帮助文本
        """
        help_text = """**🤖 生产任务助手 - 使用帮助**

**常用指令：**

📝 **报工**
报工 订单号 工序 数量 [完成]
示例：报工 ORD202604001 编织 200 完成

🔍 **查询**
查询 订单号
示例：查询 ORD202604001

📋 **任务**
任务 / 我的任务 / 待办
显示您的待处理任务列表

✅ **确认**
确认 任务ID
确认任务分配

❌ **取消**
取消 任务ID
取消任务

---

**也可以直接发送订单号查询状态！**

*发送任何内容即可获得帮助*
"""

        return help_text

    def get_help(self) -> str:
        return "帮助指令：帮助 / help / ?\n" \
               "显示所有可用指令和使用说明"
