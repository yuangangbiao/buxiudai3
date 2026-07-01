# -*- coding: utf-8 -*-
"""
统一指令处理中间件
处理来自各渠道（微信群、小程序、桌面端）的指令
"""
import re
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
from dataclasses import dataclass


class InstructionSource(Enum):
    """指令来源"""
    WECHAT = 'wechat'  # 企业微信群
    MINIPROGRAM = 'miniprogram'  # 微信小程序
    DESKTOP = 'desktop'  # 桌面端
    API = 'api'  # API接口


class InstructionType(Enum):
    """指令类型"""
    REPORT = 'report'  # 报工
    QUERY_ORDER = 'query_order'  # 查询订单
    QUERY_TASK = 'query_task'  # 查询任务
    HELP = 'help'  # 帮助
    UNKNOWN = 'unknown'  # 未知


@dataclass
class ParsedInstruction:
    """解析后的指令"""
    source: InstructionSource
    type: InstructionType
    raw_text: str
    data: Dict[str, Any]
    confidence: float = 1.0


class InstructionParser:
    """指令解析器"""

    def __init__(self):
        self.parsers: List[Callable[[str], Optional[ParsedInstruction]]] = [
            self._parse_report,
            self._parse_query_order,
            self._parse_query_task,
            self._parse_help
        ]

    def parse(self, text: str, source: InstructionSource = InstructionSource.WECHAT) -> ParsedInstruction:
        """
        解析指令

        Args:
            text: 原始文本
            source: 指令来源

        Returns:
            解析后的指令
        """
        text = text.strip()

        for parser in self.parsers:
            result = parser(text)
            if result:
                result.source = source
                result.raw_text = text
                return result

        # 未知指令
        return ParsedInstruction(
            source=source,
            type=InstructionType.UNKNOWN,
            raw_text=text,
            data={}
        )

    def _parse_report(self, text: str) -> Optional[ParsedInstruction]:
        """
        解析报工指令

        支持格式:
        - 报工 ORD202604001 编织 200
        - 报 ORD202604001 编织 200
        - 完成 ORD202604001 编织 200
        - 编织 200 完成 ORD202604001
        """
        # 报工指令模式
        patterns = [
            r'报工\s+(\w+)\s+(\S+)\s+(\d+)',
            r'报\s+(\w+)\s+(\S+)\s+(\d+)',
            r'完成\s+(\w+)\s+(\S+)\s+(\d+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                order_no = match.group(1).upper()
                process = match.group(2)
                qty = int(match.group(3))

                # 判断状态
                status = '进行中'
                if '完成' in text or '完了' in text or '结束' in text:
                    status = '已完成'

                return ParsedInstruction(
                    source=InstructionSource.WECHAT,
                    type=InstructionType.REPORT,
                    raw_text=text,
                    data={
                        'order_no': order_no,
                        'process_name': process,
                        'quantity': qty,
                        'status': status
                    },
                    confidence=0.95
                )

        # 简化格式: 工序 数量 订单（智能识别订单号）
        simple_match = re.search(r'(\S+)\s+(\d+)\s+(\S+)', text)
        if simple_match and any(kw in text for kw in ['报', '完成', '做完']):
            process = simple_match.group(1)
            qty = int(simple_match.group(2))
            potential_order = simple_match.group(3).upper()
            
            # 判断第三个是不是订单号（应该是ORD开头或数字开头）
            if potential_order.startswith('ORD') or potential_order[0].isdigit():
                order_no = potential_order
            else:
                # 不是订单号，可能是"完成"等词，尝试从文本其他地方找
                order_match = re.search(r'ORD\d+', text.upper())
                order_no = order_match.group(0) if order_match else '未知'
            
            status = '已完成' if '完成' in text else '进行中'
            
            return ParsedInstruction(
                source=InstructionSource.WECHAT,
                type=InstructionType.REPORT,
                raw_text=text,
                data={
                    'order_no': order_no,
                    'process_name': process,
                    'quantity': qty,
                    'status': status
                },
                confidence=0.8
            )

        return None

    def _parse_query_order(self, text: str) -> Optional[ParsedInstruction]:
        """
        解析订单查询指令

        支持格式:
        - 查单 ORD202604001
        - 订单 ORD202604001
        - 进度 ORD202604001
        - ORD202604001
        """
        # 提取订单号
        order_match = re.search(r'ORD\d+', text.upper())
        if order_match:
            order_no = order_match.group(0)
            return ParsedInstruction(
                source=InstructionSource.WECHAT,
                type=InstructionType.QUERY_ORDER,
                raw_text=text,
                data={
                    'order_no': order_no
                },
                confidence=0.9
            )

        # 查询关键词
        if any(kw in text for kw in ['查单', '订单', '进度', '状态']):
            return ParsedInstruction(
                source=InstructionSource.WECHAT,
                type=InstructionType.QUERY_ORDER,
                raw_text=text,
                data={
                    'needs_order': True
                },
                confidence=0.7
            )

        return None

    def _parse_query_task(self, text: str) -> Optional[ParsedInstruction]:
        """
        解析任务查询指令

        支持格式:
        - 任务
        - 我的任务
        - 待处理
        """
        if text in ['任务', '我的任务', '待处理', '查看任务']:
            return ParsedInstruction(
                source=InstructionSource.WECHAT,
                type=InstructionType.QUERY_TASK,
                raw_text=text,
                data={},
                confidence=0.95
            )

        if any(kw in text for kw in ['任务', '待办', '待处理']):
            return ParsedInstruction(
                source=InstructionSource.WECHAT,
                type=InstructionType.QUERY_TASK,
                raw_text=text,
                data={},
                confidence=0.8
            )

        return None

    def _parse_help(self, text: str) -> Optional[ParsedInstruction]:
        """
        解析帮助指令

        支持格式:
        - 帮助
        - help
        - how to use
        """
        help_keywords = ['帮助', 'help', '怎么用', '如何用', '怎么', '如何']
        if any(kw in text.lower() for kw in help_keywords):
            return ParsedInstruction(
                source=InstructionSource.WECHAT,
                type=InstructionType.HELP,
                raw_text=text,
                data={},
                confidence=0.95
            )

        return None


class ResponseGenerator:
    """响应生成器"""

    def __init__(self):
        self.templates = {
            InstructionType.REPORT: self._report_response,
            InstructionType.QUERY_ORDER: self._query_order_response,
            InstructionType.QUERY_TASK: self._query_task_response,
            InstructionType.HELP: self._help_response,
            InstructionType.UNKNOWN: self._unknown_response
        }

    def generate(self, instruction: ParsedInstruction, result: Dict = None) -> str:
        """
        生成响应

        Args:
            instruction: 解析后的指令
            result: 执行结果

        Returns:
            响应文本
        """
        generator = self.templates.get(instruction.type, self._unknown_response)
        return generator(instruction, result)

    def _report_response(self, instruction: ParsedInstruction, result: Dict) -> str:
        """报工响应"""
        data = instruction.data
        success = result.get('success', False) if result else False

        if success:
            return f"""[OK] 报工成功！
━━━━━━━━━━━━━━━━━━━━
订单: {data.get('order_no')}
工序: {data.get('process_name')}
数量: {data.get('quantity')}
状态: {data.get('status')}
操作员: {result.get('operator_name', '未知') if result else '未知'}
任务ID: {result.get('container_task_id', '未知') if result else '未知'}
━━━━━━━━━━━━━━━━━━━━"""
        else:
            return f"""[X] 报工失败
━━━━━━━━━━━━━━━━━━━━
原因: {result.get('error', '未知错误') if result else '未知错误'}
━━━━━━━━━━━━━━━━━━━━"""

    def _query_order_response(self, instruction: ParsedInstruction, result: Dict) -> str:
        """订单查询响应"""
        data = instruction.data
        order_no = data.get('order_no')

        if not order_no or data.get('needs_order'):
            return """请输入订单号查询，例如：
查单 ORD202604001"""

        tasks = result.get('tasks', []) if result else []

        if not tasks:
            return f"""订单 {order_no}
━━━━━━━━━━━━━━━━━━━━
暂无报工记录"""

        task_list = '\n'.join([
            f"  • {t.get('title')} - {t.get('status')}"
            for t in tasks[:5]
        ])

        return f"""订单 {order_no}
━━━━━━━━━━━━━━━━━━━━
报工记录:
{task_list}
━━━━━━━━━━━━━━━━━━━━
共 {len(tasks)} 条记录"""

    def _query_task_response(self, instruction: ParsedInstruction, result: Dict) -> str:
        """任务查询响应"""
        tasks = result.get('tasks', []) if result else []

        if not tasks:
            return """当前没有待处理任务
━━━━━━━━━━━━━━━━━━━━
很棒！任务都已完成！"""

        task_list = '\n'.join([
            f"  {i+1}. {t.get('title')}"
            for i, t in enumerate(tasks[:5])
        ])

        return f"""待处理任务列表
━━━━━━━━━━━━━━━━━━━━
{task_list}
━━━━━━━━━━━━━━━━━━━━
共 {len(tasks)} 个任务"""

    def _help_response(self, instruction: ParsedInstruction, result: Dict) -> str:
        """帮助响应"""
        return """报工机器人使用帮助
━━━━━━━━━━━━━━━━━━━━
文字报工:
  报 订单号 工序 数量
  示例: 报 ORD202604001 编织 200
  简写: 报、报工、完工、完成 都支持

查询订单:
  查单 订单号
  示例: 查单 ORD202604001

查看任务:
  发送: 任务

获取帮助:
  发送: 帮助
━━━━━━━━━━━━━━━━━━━━
提示: 也可以发送语音报工！"""

    def _unknown_response(self, instruction: ParsedInstruction, result: Dict) -> str:
        """未知指令响应"""
        return """我还没理解这个指令。
发送"帮助"查看支持的功能。"""


class UnifiedInstructionHandler:
    """统一指令处理器"""

    def __init__(self):
        self.parser = InstructionParser()
        self.response_generator = ResponseGenerator()
        self.executors: Dict[InstructionType, Callable] = {}
        self._register_default_executors()

    def _register_default_executors(self):
        """注册默认执行器"""
        # 这些会在运行时设置
        pass

    def set_executor(self, instruction_type: InstructionType, executor: Callable):
        """
        设置执行器

        Args:
            instruction_type: 指令类型
            executor: 执行函数
        """
        self.executors[instruction_type] = executor

    def handle(self, text: str, source: InstructionSource = InstructionSource.WECHAT,
               context: Dict = None) -> Dict[str, Any]:
        """
        处理指令

        Args:
            text: 原始文本
            source: 来源
            context: 上下文

        Returns:
            处理结果
        """
        # 1. 解析
        instruction = self.parser.parse(text, source)

        # 2. 执行
        result = {}
        executor = self.executors.get(instruction.type)
        if executor:
            try:
                result = executor(instruction, context)
            except Exception as e:
                result = {'success': False, 'error': str(e)}

        # 3. 生成响应
        response = self.response_generator.generate(instruction, result)

        return {
            'instruction': instruction,
            'result': result,
            'response': response
        }


# 全局实例
instruction_handler = UnifiedInstructionHandler()
