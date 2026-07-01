# -*- coding: utf-8 -*-
"""
外协指令模块

处理外协报工相关用户指令
"""

import re
from typing import Optional, Dict, Any

from commands.base import (
    BaseCommand, ParsedCommand, CommandResult,
    CommandType, normalize_text
)


class OutsourcCommand(BaseCommand):
    """
    外协指令

    支持格式：
    1. 外协 WO0001 热处理 100      → 完整格式：工单 工序 数量
    2. 外协 WO0001 热处理 100 7   → 带承诺天数
    3. 外协 WO0001 100            → 工单 + 数量，工序取第一个外协工序
    4. 外协 WO0001                → 只用订单号，查所有外协工序及数量
    5. 外协 0001                  → 后4位匹配
    """

    OUTSOURCE_KEYWORDS = '外协|委外|外协报工|委外加工'

    def __init__(self):
        super().__init__(
            name='外协报工',
            aliases=['外协', '委外', '外协报工', '委外加工', 'external', 'ext', 'out']
        )

    def get_patterns(self) -> list:
        kw = self.OUTSOURCE_KEYWORDS
        return [
            rf'^(?:{kw})\s+(WO\S+)\s+(\S+)\s+(\d+)\s+(\d+)',
            rf'^(?:{kw})\s+(WO\S+)\s+(\S+)\s+(\d+)',
            rf'^(?:{kw})\s+(WO\S+)\s+(\d+)',
            rf'^(?:{kw})\s+(WO\d+)',
            rf'^(?:{kw})\s+(\d{{1,4}})',
            rf'^(?:{kw})$',
        ]

    def parse(self, text: str) -> Optional[ParsedCommand]:
        normalized = normalize_text(text.strip())
        if not normalized:
            return None

        for pattern in self.get_patterns():
            m = re.match(pattern, normalized, re.IGNORECASE)
            if not m:
                continue
            groups = m.groups()
            n = len(groups)

            def wo(grp):
                s = grp.lower()
                return grp.upper() if s.startswith('wo') else grp

            if n == 5:
                return ParsedCommand(
                    raw_text=text,
                    command_type=CommandType.OUTSOURCE,
                    args={
                        'order_no': wo(groups[0]),
                        'process': groups[1],
                        'quantity': int(groups[2]),
                        'promised_days': int(groups[3]),
                    }
                )
            elif n == 4:
                return ParsedCommand(
                    raw_text=text,
                    command_type=CommandType.OUTSOURCE,
                    args={
                        'order_no': wo(groups[0]),
                        'process': groups[1],
                        'quantity': int(groups[2]),
                        'promised_days': None,
                    }
                )
            elif n == 3:
                return ParsedCommand(
                    raw_text=text,
                    command_type=CommandType.OUTSOURCE,
                    args={
                        'order_no': wo(groups[0]),
                        'process': groups[1],
                        'quantity': int(groups[2]),
                        'promised_days': None,
                    }
                )
            elif n == 2:
                suffix = groups[1]
                if re.match(r'^\d{1,4}$', suffix):
                    return ParsedCommand(
                        raw_text=text,
                        command_type=CommandType.OUTSOURCE,
                        args={
                            'short_suffix': suffix,
                            'process': None,
                            'quantity': None,
                            'promised_days': None,
                        }
                    )
                return ParsedCommand(
                    raw_text=text,
                    command_type=CommandType.OUTSOURCE,
                    args={
                        'order_no': wo(groups[1]),
                        'process': None,
                        'quantity': None,
                        'promised_days': None,
                    }
                )
            elif n == 1:
                val = groups[0]
                if re.match(r'^\d{1,4}$', val):
                    return ParsedCommand(
                        raw_text=text,
                        command_type=CommandType.OUTSOURCE,
                        args={
                            'short_suffix': val,
                            'process': None,
                            'quantity': None,
                            'promised_days': None,
                        }
                    )
                return ParsedCommand(
                    raw_text=text,
                    command_type=CommandType.OUTSOURCE,
                    args={
                        'order_no': wo(val),
                        'process': None,
                        'quantity': None,
                        'promised_days': None,
                    }
                )
            elif n == 0:
                return ParsedCommand(
                    raw_text=text,
                    command_type=CommandType.OUTSOURCE,
                    args={
                        'order_no': None,
                        'process': None,
                        'quantity': None,
                        'promised_days': None,
                    }
                )
        return None

    def execute(self, parsed: ParsedCommand, context: Dict) -> CommandResult:
        order_no = parsed.args.get('order_no')
        short_suffix = parsed.args.get('short_suffix')
        process = parsed.args.get('process')
        quantity = parsed.args.get('quantity')
        promised_days = parsed.args.get('promised_days')

        container_center = context.get('container_center')
        if not container_center:
            return CommandResult.fail(message="系统错误：容器中心未初始化")

        try:
            if short_suffix:
                all_tasks = container_center.get_all_tasks(limit=1000)
                matched = None
                for t in all_tasks:
                    related = t.get('related_order', '')
                    if related.endswith(short_suffix) and t.get('data_type') == 'outsource':
                        matched = t
                        break
                if matched:
                    order_no = matched.get('related_order')
                else:
                    return CommandResult.fail(message=f"未找到尾号 {short_suffix} 的外协任务")

            if not order_no:
                return CommandResult.fail(message="订单号不能为空，请输入：外协 WO订单号")

            records = self._get_outsource_by_order(container_center, order_no)
            if process and quantity is not None:
                return self._do_report(container_center, order_no, process, quantity, promised_days, records, context)
            elif quantity is not None and not process:
                first_process = records[0].get('content', {}).get('process_name') if records else None
                if not first_process:
                    return CommandResult.fail(message=f"工单 {order_no} 没有可外协的工序")
                return self._do_report(container_center, order_no, first_process, quantity, promised_days, records, context)
            else:
                return self._show_order_outsource(order_no, records)

        except Exception as e:
            import logging
            logging.getLogger(__name__).exception(f'[外协指令] 执行异常: {e}')
            return CommandResult.fail(message=f"外协报工异常：{str(e)}")

    def _get_outsource_by_order(self, cc, order_no: str):
        try:
            pkg_dicts = cc.storage.get_packages(limit=2000) or []
            return [p for p in pkg_dicts
                    if p.get('data_type') == 'outsource'
                    and p.get('related_order') == order_no]
        except Exception as e:
            logger.warning(f"获取外协工单 {order_no} 记录失败: {e}")
            return []

    def _do_report(self, cc, order_no, process, quantity, promised_days, records, context):
        matched = None
        for rec in records:
            content = rec.get('content', {})
            if isinstance(content, str):
                import json as _json
                content = _json.loads(content)
            if content.get('process_name') == process:
                matched = rec
                break

        if not matched:
            return CommandResult.fail(message=f"工单 {order_no} 中未找到工序「{process}」的外协任务")

        pkg_id = matched.get('id')
        status = matched.get('status', '')

        if status == 'received':
            return CommandResult.fail(message=f"工序「{process}」已完成收货，无需重复报工")

        if status == 'completed':
            return CommandResult.fail(message=f"工序「{process}」已完成，请进行收货确认")

        if status == 'processing' and promised_days is not None:
            from datetime import datetime, timedelta
            promised_date = (datetime.now() + timedelta(days=promised_days)).strftime('%Y-%m-%d %H:%M:%S')
            cc.storage.update_package(pkg_id, {
                'content': {**matched.get('content', {}),
                            'promised_days': promised_days,
                            'promised_date': promised_date,
                            'feedback_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')},
                'status': 'processing'
            })
            msg = f"工序「{process}」数量 {quantity} 已提交\n承诺完成：{promised_days} 天后（{promised_date[:10]}）"
            self._notify(cc, context, order_no, process, quantity)
            return CommandResult.success(message=msg)

        if status == 'pending':
            if promised_days is not None:
                from datetime import datetime, timedelta
                promised_date = (datetime.now() + timedelta(days=promised_days)).strftime('%Y-%m-%d %H:%M:%S')
                cc.storage.update_package(pkg_id, {
                    'content': {**matched.get('content', {}),
                                'planned_qty': quantity,
                                'promised_days': promised_days,
                                'promised_date': promised_date,
                                'feedback_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')},
                    'status': 'processing'
                })
                self._notify(cc, context, order_no, process, quantity)
                return CommandResult.success(
                    message=f"外协任务「{process}」已接单\n数量：{quantity}\n承诺：{promised_days} 天（{promised_date[:10]}）"
                )
            else:
                return CommandResult.fail(
                    message=f"工序「{process}」待反馈，请输入：外协 {order_no} {process} {quantity} [承诺天数]"
                )

        return CommandResult.fail(message=f"当前状态「{status}」不支持此操作")

    def _show_order_outsource(self, order_no: str, records: list) -> CommandResult:
        if not records:
            return CommandResult.fail(message=f"工单 {order_no} 暂无外协任务")

        lines = [f"**工单 {order_no} 外协工序：**\n"]
        for rec in records:
            content = rec.get('content', {})
            if isinstance(content, str):
                import json as _json
                content = _json.loads(content)
            process_name = content.get('process_name', '未知')
            planned_qty = content.get('planned_qty', 0)
            status = rec.get('status', 'unknown')
            promised_date = content.get('promised_date', '')
            status_icon = {'pending': '⏳', 'processing': '🔄', 'completed': '✅', 'received': '📥', 'overdue': '⚠️'}.get(status, '❓')
            date_str = f" | 承诺 {promised_date[:10]}" if promised_date else ""
            lines.append(f"{status_icon} {process_name} × {planned_qty} 【{status}】{date_str}")

        lines.append("\n格式：外协 订单号 工序 数量 [承诺天数]")
        return CommandResult.success(message="\n".join(lines))

    def _notify(self, cc, context, order_no, process, quantity):
        try:
            bot = context.get('bot')
            if bot:
                from container_config import container_config
                cfg = container_config.get_outsourc_config()
                target_op = cfg.default_operator_id
                bot.send_text(
                    f"📋 外协报工通知\n订单：{order_no}\n工序：{process}\n数量：{quantity}\n请及时处理",
                    receiver_id=target_op
                )
        except Exception as e:
            logger.warning(f"外协报工通知发送失败: {e}")

    def get_help(self) -> str:
        return """**外协报工指令格式：**
`外协 WO订单号 工序 数量 [承诺天数]`

**示例：**
- `外协 WO0001 热处理 100` - 数量报工
- `外协 WO0001 热处理 100 7` - 带承诺7天完成
- `外协 WO0001 100` - 自动取第一个外协工序
- `外协 WO0001` - 查看工单所有外协工序"""
