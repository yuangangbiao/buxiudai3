#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据边界校验模块 - 确保数据在合理范围内"""

import re
import logging
from typing import Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """校验结果"""
    is_valid: bool
    error_message: Optional[str] = None
    sanitized_value: Any = None


class DataBoundary:
    """数据边界校验器 - 验证和清理输入数据"""

    VALID_PROCESSES = ['编织', '编制', '焊接', '切割', '打磨', '质检', '检验', '包装', '入库', '出库']
    VALID_ORDER_PREFIXES = ['WO', 'W', 'wo', 'w']

    def __init__(
        self,
        max_quantity: int = 100000,
        max_order_length: int = 50,
        max_process_length: int = 20,
        max_remark_length: int = 500
    ):
        """
        初始化边界校验器

        Args:
            max_quantity: 最大数量限制
            max_order_length: 订单号最大长度
            max_process_length: 工序名称最大长度
            max_remark_length: 备注最大长度
        """
        self.max_quantity = max_quantity
        self.max_order_length = max_order_length
        self.max_process_length = max_process_length
        self.max_remark_length = max_remark_length

    def validate_order_no(self, order_no: str) -> ValidationResult:
        """
        验证订单号格式

        Args:
            order_no: 订单号

        Returns:
            ValidationResult: 校验结果
        """
        if not order_no:
            return ValidationResult(False, "订单号不能为空")

        order_no = order_no.strip()

        if len(order_no) > self.max_order_length:
            return ValidationResult(False, f"订单号长度超过限制({self.max_order_length})")

        if len(order_no) < 4:
            return ValidationResult(False, "订单号长度不足4位")

        for prefix in self.VALID_ORDER_PREFIXES:
            if order_no.upper().startswith(prefix):
                remaining = order_no[len(prefix):]
                if remaining.isdigit() and len(remaining) >= 4:
                    return ValidationResult(True, sanitized_value=order_no.upper())
                break

        if re.match(r'^\d{6,12}$', order_no):
            return ValidationResult(True, sanitized_value=order_no)

        return ValidationResult(False, f"无效的订单号格式: {order_no}")

    def validate_quantity(self, quantity: Any) -> ValidationResult:
        """
        验证数量范围

        Args:
            quantity: 数量（支持字符串和数字）

        Returns:
            ValidationResult: 校验结果
        """
        try:
            if isinstance(quantity, str):
                quantity = quantity.strip()
                if not quantity:
                    return ValidationResult(False, "数量不能为空")
                quantity = int(quantity)
        except (ValueError, TypeError):
            return ValidationResult(False, f"无效的数量格式: {quantity}")

        if not isinstance(quantity, int):
            return ValidationResult(False, f"数量必须为整数: {quantity}")

        if quantity <= 0:
            return ValidationResult(False, f"数量必须为正数: {quantity}")

        if quantity > self.max_quantity:
            return ValidationResult(False, f"数量超过限制({self.max_quantity}): {quantity}")

        return ValidationResult(True, sanitized_value=quantity)

    def validate_process(self, process: str) -> ValidationResult:
        """
        验证工序名称
        主软件同步时直接信任传入值，只做格式校验
        微信端报工由 container_center.get_task_by_order 做工序匹配
        """
        if not process:
            return ValidationResult(False, "工序名称不能为空")

        process = process.strip()

        if len(process) > self.max_process_length:
            return ValidationResult(False, f"工序名称过长({self.max_process_length}): {process}")

        return ValidationResult(True, sanitized_value=process)

    def validate_remark(self, remark: Optional[str]) -> ValidationResult:
        """
        验证备注长度

        Args:
            remark: 备注内容

        Returns:
            ValidationResult: 校验结果
        """
        if not remark:
            return ValidationResult(True, sanitized_value="")

        remark = str(remark).strip()

        if len(remark) > self.max_remark_length:
            return ValidationResult(
                False,
                f"备注长度超过限制({self.max_remark_length}): {len(remark)}字符"
            )

        return ValidationResult(True, sanitized_value=remark)

    def validate_user_id(self, user_id: Any) -> ValidationResult:
        """
        验证用户ID

        Args:
            user_id: 用户ID

        Returns:
            ValidationResult: 校验结果
        """
        if not user_id:
            return ValidationResult(False, "用户ID不能为空")

        user_id = str(user_id).strip()

        if len(user_id) > 50:
            return ValidationResult(False, f"用户ID过长: {user_id}")

        if re.match(r'^[a-zA-Z0-9_-]+$', user_id):
            return ValidationResult(True, sanitized_value=user_id)

        return ValidationResult(False, f"无效的用户ID格式: {user_id}")

    def validate_ip_address(self, ip: str) -> ValidationResult:
        """
        验证IP地址格式

        Args:
            ip: IP地址

        Returns:
            ValidationResult: 校验结果
        """
        if not ip:
            return ValidationResult(False, "IP地址不能为空")

        ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if re.match(ipv4_pattern, ip):
            parts = ip.split('.')
            if all(0 <= int(part) <= 255 for part in parts):
                return ValidationResult(True, sanitized_value=ip)

        return ValidationResult(False, f"无效的IP地址格式: {ip}")

    def sanitize_input(self, input_str: str) -> str:
        """
        清理输入字符串（移除危险字符）

        Args:
            input_str: 输入字符串

        Returns:
            str: 清理后的字符串
        """
        if not input_str:
            return ""

        dangerous_chars = ['<', '>', '"', "'", '&', ';', '|', '`', '$', '(', ')']
        result = input_str

        for char in dangerous_chars:
            result = result.replace(char, '')

        return result.strip()

    def validate_report_request(
        self,
        order_no: str,
        process: str,
        quantity: Any,
        user_id: str
    ) -> tuple[bool, Optional[str]]:
        """
        综合验证报工请求

        Args:
            order_no: 订单号
            process: 工序
            quantity: 数量
            user_id: 用户ID

        Returns:
            tuple: (是否有效, 错误信息)
        """
        order_result = self.validate_order_no(order_no)
        if not order_result.is_valid:
            return False, order_result.error_message

        process_result = self.validate_process(process)
        if not process_result.is_valid:
            return False, process_result.error_message

        quantity_result = self.validate_quantity(quantity)
        if not quantity_result.is_valid:
            return False, quantity_result.error_message

        user_result = self.validate_user_id(user_id)
        if not user_result.is_valid:
            return False, user_result.error_message

        return True, None

    def get_valid_processes(self) -> List[str]:
        """获取所有已出现的工序列表（从容器中心动态获取）"""
        try:
            from wechat_server import container_center
            if container_center:
                packages = container_center.storage.get_packages(limit=1000)
                processes = set()
                for pkg in packages:
                    pn = pkg.get('related_process') or pkg.get('content', {}).get('process_name', '')
                    if pn:
                        processes.add(pn)
                return sorted(list(processes))
        except Exception as e:
            logger.warning(f"获取动态工序列表失败: {e}")
        return []


data_boundary = DataBoundary()
